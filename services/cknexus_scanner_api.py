"""Least-privilege local scanner API for CK-NEXUS.

This service is deliberately fail-closed: it scans only a clean Git checkout,
records commit/tree provenance, and never promotes a scan to VERIFIED.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(
    os.environ.get("CKNEXUS_SCAN_ROOT", "/opt/actions-runner/_work/ck-nexus/ck-nexus")
).resolve()
TOKEN_FILE = Path(
    os.environ.get(
        "CKNEXUS_SCANNER_TOKEN_FILE",
        "/etc/cknexus-scanner/token",
    )
)
EVIDENCE_DIR = Path(
    os.environ.get("CKNEXUS_SCAN_EVIDENCE_DIR", "/opt/cknexus/evidence/scans")
).resolve()
TRIVY_BIN = os.environ.get("CKNEXUS_TRIVY_BIN", "/usr/local/bin/trivy")
SEMGREP_BIN = os.environ.get("CKNEXUS_SEMGREP_BIN", "/usr/local/bin/semgrep")
MAX_BODY_BYTES = 1_048_576
ALLOWED_SCANNERS = frozenset({"trivy", "semgrep"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ScannerError(RuntimeError):
    """A scanner could not produce parseable result data."""


def _source_identity(root: Path) -> dict[str, str]:
    """Return a commit/tree identity only for a clean worktree."""
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    commit = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    dirty = git("status", "--porcelain", "--untracked-files=all")
    if not SHA_RE.fullmatch(commit) or not SHA_RE.fullmatch(tree):
        raise ScannerError("invalid_source_identity")
    if dirty:
        raise ScannerError("source_not_clean")
    return {"source_sha": commit, "source_tree": tree}


def _run_scanner(name: str, root: Path) -> dict[str, Any]:
    binary = TRIVY_BIN if name == "trivy" else SEMGREP_BIN
    if not Path(binary).is_file():
        raise ScannerError("scanner_unavailable")
    with tempfile.NamedTemporaryFile(prefix="cknexus-scan-", suffix=".json", delete=False) as tmp:
        output_path = Path(tmp.name)
    try:
        if name == "trivy":
            command = [
                binary, "fs", "--scanners", "vuln,secret", "--format", "json",
                "--output", str(output_path), ".",
            ]
        else:
            command = [
                binary, "scan", "--config", "auto", "--json",
                "--output", str(output_path), ".",
            ]
        result = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScannerError("scanner_output_invalid") from exc
        if name == "trivy":
            results = data.get("Results") or []
            vulnerabilities = sum(len(item.get("Vulnerabilities") or []) for item in results)
            secrets_found = sum(len(item.get("Secrets") or []) for item in results)
            summary = {
                "exit_code": result.returncode,
                "vulnerabilities": vulnerabilities,
                "secrets": secrets_found,
            }
        else:
            summary = {
                "exit_code": result.returncode,
                "findings": len(data.get("results") or []),
                "errors": len(data.get("errors") or []),
            }
        return summary
    except subprocess.TimeoutExpired as exc:
        raise ScannerError("scanner_timeout") from exc
    finally:
        output_path.unlink(missing_ok=True)


def create_handler(
    repo_root: Path = REPO_ROOT,
    token_file: Path = TOKEN_FILE,
    evidence_dir: Path = EVIDENCE_DIR,
):
    root = repo_root.resolve()
    token_path = token_file
    evidence_path = evidence_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args: object) -> None:
            # Request paths and headers may contain user-controlled material.
            return

        def _reply(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._reply(200, {"status": "ok", "service": "cknexus-scanner-api"})
            else:
                self._reply(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/api/scan":
                self._reply(404, {"error": "not_found"})
                return
            try:
                expected_token = token_path.read_bytes().strip()
                supplied_header = self.headers.get("Authorization", "")
                supplied = supplied_header.encode("utf-8", errors="strict")
                expected = b"Bearer " + expected_token
                if not expected_token or not secrets.compare_digest(supplied, expected):
                    self._reply(401, {"error": "unauthorized"})
                    return
            except (OSError, UnicodeError):
                self._reply(503, {"error": "credential_unavailable"})
                return

            length_text = self.headers.get("Content-Length", "")
            if not length_text.isascii() or not length_text.isdigit():
                self._reply(400, {"error": "invalid_content_length"})
                return
            length = int(length_text)
            if length <= 0 or length > MAX_BODY_BYTES:
                self._reply(400, {"error": "invalid_content_length"})
                return
            try:
                request = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._reply(400, {"error": "invalid_json"})
                return
            if not isinstance(request, dict):
                self._reply(400, {"error": "invalid_request"})
                return
            target = request.get("target")
            if not isinstance(target, str):
                self._reply(400, {"error": "target_not_allowed"})
                return
            try:
                if Path(target).resolve() != root:
                    self._reply(400, {"error": "target_not_allowed"})
                    return
            except (OSError, RuntimeError, ValueError):
                self._reply(400, {"error": "target_not_allowed"})
                return

            raw_scanners = request.get("scanners", ["trivy", "semgrep"])
            if isinstance(raw_scanners, str):
                scanners = [part.strip() for part in raw_scanners.split(",") if part.strip()]
            elif isinstance(raw_scanners, list) and all(isinstance(x, str) for x in raw_scanners):
                scanners = list(dict.fromkeys(x.strip() for x in raw_scanners if x.strip()))
            else:
                self._reply(400, {"error": "invalid_scanners"})
                return
            if not scanners or any(name not in ALLOWED_SCANNERS for name in scanners):
                self._reply(400, {"error": "no_allowed_scanners"})
                return

            try:
                identity = _source_identity(root)
            except ScannerError as exc:
                status = 409 if str(exc) == "source_not_clean" else 503
                self._reply(status, {"error": str(exc)})
                return
            except (OSError, subprocess.SubprocessError):
                self._reply(503, {"error": "source_identity_unavailable"})
                return

            try:
                summaries = {name: _run_scanner(name, root) for name in scanners}
                evidence_path.mkdir(parents=True, exist_ok=True)
                scan_id = "scan-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + secrets.token_hex(4)
                artifact = {
                    "schema_version": 2,
                    "scan_id": scan_id,
                    "source_sha": identity["source_sha"],
                    "source_tree": identity["source_tree"],
                    "source_state": "CLEAN",
                    "summary": summaries,
                    "status": "EXECUTED_NOT_VERIFIED",
                }
                raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
                digest = hashlib.sha256(raw).hexdigest()
                destination = evidence_path / (scan_id + ".json")
                fd, temp_name = tempfile.mkstemp(prefix=".scan-", dir=evidence_path)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temp_name, 0o600)
                    os.replace(temp_name, destination)
                finally:
                    Path(temp_name).unlink(missing_ok=True)
                self._reply(200, {**artifact, "artifact_sha256": digest})
            except ScannerError as exc:
                self._reply(502, {"error": str(exc)})
            except (OSError, subprocess.SubprocessError, ValueError):
                self._reply(502, {"error": "scan_execution_failed"})

    return Handler


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8787), create_handler())
    server.serve_forever()


if __name__ == "__main__":
    main()
