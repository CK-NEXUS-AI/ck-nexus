"""CK-NEXUS Bootstrap v5.2.3: fail-closed evidence runner.

This module is intentionally not wired into production services. Use only a
predefined test profile; never pass an arbitrary shell command.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "bootstrap-tests": (
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_ck_nexus_bootstrap_v523.py",
        "-v",
    ),
}
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


class EvidenceError(RuntimeError):
    pass


def validate_name(name: str) -> None:
    if not isinstance(name, str) or not SAFE_NAME.fullmatch(name) or name in {".", ".."}:
        raise ValueError("invalid single-component name")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SecurePathManager:
    @staticmethod
    def create_run_dir(base_dir: str, run_id: str) -> tuple[Path, int]:
        validate_name(run_id)
        if not isinstance(base_dir, str) or not os.path.isabs(base_dir):
            raise ValueError("evidence base must be absolute")
        raw = os.path.abspath(base_dir)
        parts = [p for p in raw.split(os.sep) if p]
        fd = os.open(os.sep, DIR_FLAGS)
        try:
            for part in parts:
                validate_name(part)
                nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
                os.close(fd)
                fd = nxt
            os.mkdir(run_id, mode=0o700, dir_fd=fd)
            run_fd = os.open(run_id, DIR_FLAGS, dir_fd=fd)
            st = os.fstat(run_fd)
            if not stat.S_ISDIR(st.st_mode):
                os.close(run_fd)
                raise EvidenceError("run path is not a directory")
            return Path(raw) / run_id, run_fd
        finally:
            os.close(fd)


class EvidenceStore:
    """Local integrity checks; not an authenticated tamper-proof trust anchor.

    The hash chain detects accidental corruption and edits that do not also
    rewrite the chain. A writer with access to this directory can recompute it.
    Production evidence must be externally signed or anchored in an append-only
    store before it is treated as independently tamper-evident.
    """

    def __init__(self, run_dir: Path, run_fd: int):
        self.run_dir = run_dir
        self.run_fd = run_fd
        self._tracking: dict[str, dict[str, Any]] = {}

    def _read_file(self, name: str) -> bytes:
        validate_name(name)
        fd = os.open(name, FILE_FLAGS, dir_fd=self.run_fd)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise EvidenceError(f"not a regular evidence file: {name}")
            chunks = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        finally:
            os.close(fd)

    def write_artifact(self, name: str, content: bytes) -> dict[str, Any]:
        validate_name(name)
        fd = os.open(name, WRITE_FLAGS, 0o600, dir_fd=self.run_fd)
        written = 0
        self._tracking[name] = {"state": "OPENED", "written": 0, "expected": len(content)}
        try:
            while written < len(content):
                n = os.write(fd, content[written:])
                if n <= 0:
                    raise OSError("zero-byte write")
                written += n
                self._tracking[name]["written"] = written
            os.fsync(fd)
            self._tracking[name]["state"] = "SYNCED"
        except Exception:
            self._tracking[name]["state"] = "FAILED"
            raise
        finally:
            os.close(fd)
        os.fsync(self.run_fd)
        actual = self._read_file(name)
        digest = sha256(actual)
        if actual != content:
            raise EvidenceError(f"read-back mismatch: {name}")
        return {"stored_size_bytes": len(actual), "sha256": digest}

    def _load_chain_locked(self) -> list[dict[str, Any]]:
        try:
            raw_bytes = self._read_file("chain.json")
        except FileNotFoundError:
            return []
        try:
            records = json.loads(raw_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceError("chain JSON is corrupt") from exc
        if not isinstance(records, list):
            raise EvidenceError("chain root must be a list")
        previous = "0" * 64
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                raise EvidenceError(f"invalid chain record at {idx}")
            required = {
                "idx",
                "artifact",
                "timestamp",
                "sha256",
                "size_bytes",
                "prev_record_hash",
                "record_hash",
                "exit_code",
                "truncated",
            }
            if not required.issubset(rec):
                raise EvidenceError(f"missing fields at chain index {idx}")
            if rec["idx"] != idx or rec["prev_record_hash"] != previous:
                raise EvidenceError(f"broken sequence/linkage at chain index {idx}")
            validate_name(rec["artifact"])
            unhashed = {k: v for k, v in rec.items() if k != "record_hash"}
            if sha256(canonical_json(unhashed)) != rec["record_hash"]:
                raise EvidenceError(f"record hash mismatch at chain index {idx}")
            artifact = self._read_file(rec["artifact"])
            if len(artifact) != rec["size_bytes"] or sha256(artifact) != rec["sha256"]:
                raise EvidenceError(f"artifact hash/size mismatch: {rec['artifact']}")
            previous = rec["record_hash"]
        return records

    def append_lineage(self, artifact: str, meta: dict[str, Any]) -> None:
        validate_name(artifact)
        reserved = {
            "idx",
            "artifact",
            "timestamp",
            "sha256",
            "size_bytes",
            "prev_record_hash",
            "record_hash",
        }
        if reserved.intersection(meta):
            raise ValueError("metadata contains reserved fields")
        lock_fd = os.open(
            ".chain.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=self.run_fd
        )
        try:
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                raise EvidenceError("chain lock is not a regular file")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            records = self._load_chain_locked()
            artifact_bytes = self._read_file(artifact)
            prev = records[-1]["record_hash"] if records else "0" * 64
            record = {
                "idx": len(records),
                "artifact": artifact,
                "timestamp": datetime.now(UTC).isoformat(),
                "sha256": sha256(artifact_bytes),
                "size_bytes": len(artifact_bytes),
                "prev_record_hash": prev,
                **meta,
            }
            record["record_hash"] = sha256(canonical_json(record))
            records.append(record)
            tmp = f".chain.tmp.{os.getpid()}.{secrets.token_hex(8)}"
            tmp_fd = os.open(tmp, WRITE_FLAGS, 0o600, dir_fd=self.run_fd)
            try:
                payload = canonical_json(records) + b"\n"
                offset = 0
                while offset < len(payload):
                    n = os.write(tmp_fd, payload[offset:])
                    if n <= 0:
                        raise OSError("zero-byte chain write")
                    offset += n
                os.fsync(tmp_fd)
            except Exception:
                os.close(tmp_fd)
                with contextlib.suppress(OSError):
                    os.unlink(tmp, dir_fd=self.run_fd)
                raise
            else:
                os.close(tmp_fd)
            try:
                os.replace(tmp, "chain.json", src_dir_fd=self.run_fd, dst_dir_fd=self.run_fd)
                os.fsync(self.run_fd)
            except Exception:
                with contextlib.suppress(OSError):
                    os.unlink(tmp, dir_fd=self.run_fd)
                raise
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)

    def reconcile(self) -> dict[str, Any]:
        lock_fd = os.open(
            ".chain.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=self.run_fd
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            records = self._load_chain_locked()
            return {
                "chain_intact": bool(records),
                "records": len(records),
                "recovery_log": [],
                "trust_boundary": (
                    "local_hash_chain_only_not_authenticated_against_same_user_writer"
                ),
            }
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


def _run_bounded(
    argv: tuple[str, ...], cwd: str, timeout: float, limit: int
) -> tuple[bytes, int, bool, bool, int]:
    """Drain child output under both an execution and pipe-drain deadline.

    The retained output is capped at ``limit`` bytes. On timeout, terminate the
    process group, escalate to SIGKILL, and stop waiting for inherited pipe FDs
    after a short bounded drain period. A descendant that escapes the process
    group must not be able to keep this function blocked forever by holding the
    stdout pipe open.
    """
    kept = bytearray()
    total = 0
    timed_out = False
    term_sent_at: float | None = None
    drain_deadline: float | None = None
    started = time.monotonic()
    deadline = started + max(0.0, timeout)
    term_grace = 0.5
    drain_grace = 0.25
    proc = subprocess.Popen(
        list(argv),
        shell=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        bufsize=0,
    )
    try:
        assert proc.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while selector.get_map() or proc.poll() is None:
                now = time.monotonic()
                if not timed_out and now >= deadline:
                    timed_out = True
                    term_sent_at = now
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGTERM)
                elif (
                    timed_out
                    and term_sent_at is not None
                    and now - term_sent_at >= term_grace
                ):
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    term_sent_at = None
                    drain_deadline = now + drain_grace
                if drain_deadline is not None and now >= drain_deadline:
                    break
                wait_for = 0.05
                if not timed_out:
                    wait_for = min(wait_for, max(0.0, deadline - now))
                elif term_sent_at is not None:
                    wait_for = min(wait_for, max(0.0, term_grace - (now - term_sent_at)))
                elif drain_deadline is not None:
                    wait_for = min(wait_for, max(0.0, drain_deadline - now))
                events = selector.select(timeout=wait_for)
                for key, _ in events:
                    try:
                        chunk = os.read(key.fd, 65536)
                    except InterruptedError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    remaining = limit - len(kept)
                    if remaining > 0:
                        kept.extend(chunk[:remaining])
            # Closing our read end is intentional when a descendant retains the
            # pipe beyond the deadline; EOF is not a prerequisite for returning.
            if selector.get_map():
                selector.unregister(proc.stdout)
    finally:
        if proc.stdout is not None and not proc.stdout.closed:
            proc.stdout.close()
    try:
        return_code = proc.wait(timeout=0.25)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        try:
            return_code = proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            # Do not call an unbounded wait here: a process stuck in kernel
            # uninterruptible sleep must not defeat the caller's deadline.
            return_code = 124
            timed_out = True
    if timed_out:
        return_code = 124
    return bytes(kept), return_code, timed_out, total > len(kept), total


def execute(profile: str, evidence_base: str, timeout: int = 300) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "UNKNOWN",
        "exit_code": 125,
        "infra_failure": False,
        "evidence_failure": False,
        "terminal_recorded": False,
    }
    run_fd = None
    store = None
    try:
        if profile not in PROFILES:
            result.update(status="POLICY_REJECTED", exit_code=126)
            return result
        run_id = datetime.now(UTC).strftime("run_%Y%m%dT%H%M%S_") + secrets.token_hex(4)
        run_dir, run_fd = SecurePathManager.create_run_dir(evidence_base, run_id)
        store = EvidenceStore(run_dir, run_fd)
        limit = 1_048_576
        stored, process_code, timed_out, truncated, total_output_bytes = _run_bounded(
            PROFILES[profile], str(PROJECT_ROOT), timeout, limit
        )
        if timed_out:
            marker = b"\n[PROCESS TIMEOUT]\n"
            kept_output_bytes = max(0, limit - len(marker))
            truncated = truncated or total_output_bytes > kept_output_bytes
            stored = stored[:kept_output_bytes] + marker
        write_meta = store.write_artifact("terminal.log", stored)
        store.append_lineage(
            "terminal.log",
            {
                "exit_code": process_code,
                "truncated": truncated,
                "original_size_bytes": total_output_bytes,
                "stored_size_bytes": len(stored),
                "output_sha256": write_meta["sha256"],
                "timed_out": timed_out,
            },
        )
        result["terminal_recorded"] = True
        result["status"] = "TEST_FAILURE" if process_code else "PASS"
        result["exit_code"] = process_code
    except Exception as exc:
        result.update(
            status="EVIDENCE_INCOMPLETE",
            exit_code=126,
            infra_failure=True,
            evidence_failure=True,
            error_type=type(exc).__name__,
            error=str(exc)[:500],
        )
    finally:
        if store is not None:
            try:
                reconciled = store.reconcile()
                if not reconciled["chain_intact"]:
                    result.update(
                        status="RECONCILIATION_FAILED", exit_code=127, evidence_failure=True
                    )
                result["reconciliation"] = reconciled
            except Exception as exc:
                result.update(
                    status="RECONCILIATION_FAILED",
                    exit_code=127,
                    evidence_failure=True,
                    reconciliation_error=type(exc).__name__,
                )
        if run_fd is not None:
            os.close(run_fd)
    return result


def main() -> int:
    base = os.environ.get("CKNEXUS_EVIDENCE_BASE", "/opt/cknexus/evidence")
    result = execute("bootstrap-tests", base)
    print(json.dumps(result, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
