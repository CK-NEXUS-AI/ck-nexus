#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REQUIRED_GATES = [
    "P0-OPS",
    "P0-EMAIL-001", "P0-EMAIL-002", "P0-EMAIL-003", "P0-EMAIL-004",
    "P0-EMAIL-005", "P0-EMAIL-006", "P0-EMAIL-007", "P0-BACKUP-001",
    "P0-AI-001", "P0-SEC-001", "P0-OBS-001", "P0-OPS-001",
]
VALID = {"PASS", "FAIL", "BLOCKED", "N/A"}
ROOT = Path(__file__).resolve().parents[1]
COMPOSE = Path(os.getenv("CKNEXUS_COMPOSE_FILE", str(ROOT / "docker-compose.p0.yml")))


def now() -> str:
    return datetime.now(UTC).isoformat()


def run(cmd: list[str], *, timeout: int = 300, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=env)


def sha256_tree(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(x in path.parts for x in {".git", "evidence", "__pycache__", ".pytest_cache"}):
            continue
        rel = path.relative_to(root).as_posix().encode()
        h.update(rel + b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def git_identity() -> tuple[str | None, str | None, int | None]:
    if not (ROOT / ".git").exists():
        supplied = os.getenv("CKNEXUS_SOURCE_COMMIT", "").strip()
        return (supplied or None, None, None)
    commit = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    branch = run(["git", "branch", "--show-current"]).stdout.strip()
    dirty = len([x for x in run(["git", "status", "--porcelain"]).stdout.splitlines() if x.strip()])
    return commit, branch, dirty


class Evidence:
    def __init__(self, base: Path, manifest: dict[str, object]) -> None:
        self.base = base
        self.manifest = manifest
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "logs").mkdir(exist_ok=True)
        (self.base / "artifacts").mkdir(exist_ok=True)
        self.write_json("manifest.json", manifest)

    def write_json(self, name: str, data: dict[str, object]) -> None:
        (self.base / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def gate(self, gate_id: str, status: str, *, command: str = "", exit_code: int | None = None,
             evidence_files: list[str] | None = None, details: dict[str, object] | None = None,
             correlation_id: str | None = None) -> dict[str, object]:
        if status not in VALID:
            raise ValueError(status)
        record = {
            "runbook_id": self.manifest["runbook_id"],
            "commit_hash": self.manifest["commit_hash"],
            "source_sha256": self.manifest["source_sha256"],
            "environment_id": self.manifest["environment_id"],
            "gate_id": gate_id,
            "status": status,
            "started_at": now(),
            "completed_at": now(),
            "command": command,
            "exit_code": exit_code,
            "evidence_files": evidence_files or [],
            "correlation_id": correlation_id,
            "service_versions": self.manifest.get("service_versions", {}),
            "details": details or {},
        }
        self.write_json(f"{gate_id}.json", record)
        return record


def docker_available() -> bool:
    try:
        return run(["docker", "version"], timeout=30).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def compose(*args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return run(["docker", "compose", "-f", str(COMPOSE), *args], timeout=timeout)


def wait_http(url: str, seconds: int = 120) -> bool:
    import urllib.request
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except Exception:
            time.sleep(2)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=str(ROOT / ".env.prod"))
    ap.add_argument("--allow-destructive", action="store_true")
    args = ap.parse_args()

    commit, branch, dirty = git_identity()
    source_sha = sha256_tree(ROOT)
    runbook_id = f"p0-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    env_id = f"{socket.gethostname()}-{os.getuid()}-{int(time.time())}"
    evidence_root = Path(os.getenv("CKNEXUS_EVIDENCE_ROOT", "/var/tmp/cknexus-evidence")) / runbook_id
    manifest = {
        "runbook_id": runbook_id,
        "commit_hash": commit,
        "source_sha256": source_sha,
        "environment_id": env_id,
        "started_at": now(),
        "git_branch": branch,
        "git_dirty_files": dirty,
        "service_versions": {},
    }
    ev = Evidence(evidence_root, manifest)

    if not commit:
        ev.gate("P0-OPS", "BLOCKED", details={"reason": "No Git metadata and CKNEXUS_SOURCE_COMMIT not supplied"})
        print(f"BLOCKED: set CKNEXUS_SOURCE_COMMIT to the immutable source commit. Evidence: {evidence_root}")
        return 2
    if dirty not in (None, 0):
        ev.gate("P0-OPS", "FAIL", details={"reason": "Dirty Git working tree", "dirty_files": dirty})
        return 1
    if not docker_available():
        ev.gate("P0-OPS", "BLOCKED", details={"reason": "Docker unavailable"})
        return 2

    env_path = Path(args.env_file)
    if not env_path.exists():
        ev.gate("P0-OPS", "BLOCKED", details={"reason": f"Missing env file: {env_path}"})
        return 2

    env = os.environ.copy()
    env["CKNEXUS_COMPOSE_FILE"] = str(COMPOSE)
    env["CKNEXUS_ENV_FILE"] = str(env_path)
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env.setdefault(k, v)

    up = run(["docker", "compose", "--env-file", str(env_path), "-f", str(COMPOSE), "up", "-d", "--build", "db", "app", "n8n-db", "n8n"], timeout=900, env=env)
    (evidence_root / "logs" / "P0-OPS-compose.log").write_text(up.stdout + "\n" + up.stderr, encoding="utf-8")
    if up.returncode != 0 or not wait_http(f"http://127.0.0.1:{env.get('CKNEXUS_PORT','8000')}/health", 180):
        ev.gate("P0-OPS", "FAIL", command="docker compose up", exit_code=up.returncode,
                evidence_files=["logs/P0-OPS-compose.log"], details={"reason": "Stack did not become healthy"})
        return 1
    # Bind service versions/image identifiers into the evidence manifest before any gate is promoted.
    versions = {}
    version_cmds = {
        "postgres": ["docker", "compose", "--env-file", str(env_path), "-f", str(COMPOSE), "exec", "-T", "db", "postgres", "--version"],
        "n8n": ["docker", "compose", "--env-file", str(env_path), "-f", str(COMPOSE), "exec", "-T", "n8n", "n8n", "--version"],
        "python": ["docker", "compose", "--env-file", str(env_path), "-f", str(COMPOSE), "exec", "-T", "app", "python", "--version"],
    }
    for name, cmd in version_cmds.items():
        vp = run(cmd, timeout=60, env=env)
        versions[name] = (vp.stdout or vp.stderr).strip()
    manifest["service_versions"] = versions
    ev.manifest = manifest
    ev.write_json("manifest.json", manifest)
    ev.gate("P0-OPS", "PASS", command="docker compose up", exit_code=0, evidence_files=["logs/P0-OPS-compose.log"], details={"service_versions": versions})

    # PostgreSQL 100-way atomic idempotency. The test script must emit JSON and fail nonzero.
    c = run([sys.executable, "scripts/test_duplicate_concurrency.py", "--require-postgres"], timeout=180, env=env)
    (evidence_root / "logs" / "P0-EMAIL-001.log").write_text(c.stdout + "\n" + c.stderr, encoding="utf-8")
    ev.gate("P0-EMAIL-001", "PASS" if c.returncode == 0 else "FAIL", command="python scripts/test_duplicate_concurrency.py",
            exit_code=c.returncode, evidence_files=["logs/P0-EMAIL-001.log"])
    if c.returncode != 0:
        return 1

    # The remaining gates are executed by dedicated scripts. Missing prerequisites are BLOCKED, never PASS.
    gate_scripts = {
        "P0-EMAIL-002": "scripts/gate_outbox_timeout.py",
        "P0-EMAIL-003": "scripts/gate_lease_recovery.py",
        "P0-EMAIL-004": "scripts/gate_n8n_routing.py",
        "P0-EMAIL-005": "scripts/gate_attachment_quarantine.py",
        "P0-EMAIL-006": "scripts/gate_loop_prevention.py",
        "P0-EMAIL-007": "scripts/gate_audit_trace.py",
        "P0-AI-001": "scripts/test_openai_live.py",
        "P0-SEC-001": "scripts/p0_security_gate.sh",
        "P0-OBS-001": "scripts/gate_observability.py",
        "P0-OPS-001": "scripts/gate_clean_machine.py",
    }
    for gate_id, script in gate_scripts.items():
        path = ROOT / script
        if not path.exists():
            ev.gate(gate_id, "BLOCKED", details={"reason": f"Missing gate script: {script}"})
            continue
        cmd = ["bash", str(path)] if path.suffix == ".sh" else [sys.executable, str(path)]
        p = run(cmd, timeout=900, env=env)
        log = f"logs/{gate_id}.log"
        (evidence_root / log).write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
        status = "PASS" if p.returncode == 0 else ("BLOCKED" if p.returncode == 2 else "FAIL")
        ev.gate(gate_id, status, command=" ".join(cmd), exit_code=p.returncode, evidence_files=[log])
        if status == "FAIL":
            return 1

    if not args.allow_destructive or env.get("CKNEXUS_ENVIRONMENT") != "staging":
        ev.gate("P0-BACKUP-001", "BLOCKED", details={
            "reason": "Destructive restore requires --allow-destructive and CKNEXUS_ENVIRONMENT=staging"
        })
    else:
        p = run(["bash", "scripts/gate_backup_restore.sh"], timeout=1800, env=env)
        log = "logs/P0-BACKUP-001.log"
        (evidence_root / log).write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
        ev.gate("P0-BACKUP-001", "PASS" if p.returncode == 0 else ("BLOCKED" if p.returncode == 2 else "FAIL"),
                command="bash scripts/gate_backup_restore.sh", exit_code=p.returncode, evidence_files=[log])

    records = {}
    for gate_id in REQUIRED_GATES:
        p = evidence_root / f"{gate_id}.json"
        if p.exists():
            records[gate_id] = json.loads(p.read_text(encoding="utf-8"))
    missing = [g for g in REQUIRED_GATES if g not in records]
    nonpass = [g for g, r in records.items() if r.get("status") != "PASS"]
    unique_commits = sorted({r.get("commit_hash") for r in records.values()})
    unique_envs = sorted({r.get("environment_id") for r in records.values()})
    final_status = "PASS" if not missing and not nonpass and len(unique_commits) == 1 and len(unique_envs) == 1 else "NO-GO"
    final = {
        "runbook_id": runbook_id,
        "status": final_status,
        "required_gates": REQUIRED_GATES,
        "missing_gates": missing,
        "non_pass_gates": nonpass,
        "unique_commits": unique_commits,
        "unique_environments": unique_envs,
        "completed_at": now(),
    }
    ev.write_json("FINAL-GATE.json", final)
    print(json.dumps(final, indent=2))
    print(f"Evidence: {evidence_root}")
    return 0 if final_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
