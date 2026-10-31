#!/usr/bin/env python3
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

R = Path("/opt/actions-runner/_work/ck-nexus/ck-nexus").resolve()
T = Path("/etc/cknexus-scanner/token")
E = Path("/opt/cknexus/evidence/scans")
E.mkdir(parents=True, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def out(self, c, o):
        b = json.dumps(o, separators=(",", ":")).encode()
        self.send_response(c)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.out(
            200, {"status": "ok", "service": "cknexus-scanner-api"}
        ) if self.path == "/health" else self.out(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/scan":
            return self.out(404, {"error": "not_found"})
        try:
            expected = ("Bearer " + T.read_text(encoding="utf-8").strip()).encode("utf-8")
            supplied = self.headers.get("Authorization", "").encode("utf-8")
            if not secrets.compare_digest(supplied, expected):
                return self.out(401, {"error": "unauthorized"})
        except (OSError, UnicodeError):
            return self.out(503, {"error": "credential_unavailable"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1048576:
                return self.out(400, {"error": "invalid_content_length"})
            try:
                d = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.out(400, {"error": "invalid_json"})
            if not isinstance(d, dict):
                return self.out(400, {"error": "invalid_request"})
            if Path(d.get("target", "")).resolve() != R:
                return self.out(400, {"error": "target_not_allowed"})
            rawss = d.get("scanners", "trivy,semgrep")
            vals = rawss if isinstance(rawss, list) else str(rawss).split(",")
            ss = [str(x).strip() for x in vals if str(x).strip() in {"trivy", "semgrep"}]
            if not ss:
                return self.out(400, {"error": "no_allowed_scanners"})
            sid = (
                "scan-"
                + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
                + "-"
                + secrets.token_hex(4)
            )
            o = {"scan_id": sid, "ref": d.get("ref", "HEAD"), "target": str(R), "summary": {}}
            if "trivy" in ss:
                with tempfile.NamedTemporaryFile(delete=False) as temp:
                    output_path = temp.name
                try:
                    p = subprocess.run(
                        [
                            "/usr/local/bin/trivy",
                            "fs",
                            "--scanners",
                            "vuln,secret",
                            "--format",
                            "json",
                            "--output",
                            output_path,
                            ".",
                        ],
                        cwd=R,
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )
                    z = json.loads(Path(output_path).read_text(encoding="utf-8"))
                finally:
                    os.unlink(output_path)
                v = [v for r in z.get("Results", []) for v in r.get("Vulnerabilities", [])]
                o["summary"]["trivy"] = {
                    "exit_code": p.returncode,
                    "vulnerabilities": len(v),
                    "secrets": sum(len(r.get("Secrets") or []) for r in z.get("Results", [])),
                }
            if "semgrep" in ss:
                with tempfile.NamedTemporaryFile(delete=False) as temp:
                    output_path = temp.name
                try:
                    p = subprocess.run(
                        [
                            "/usr/local/bin/semgrep",
                            "scan",
                            "--config",
                            "auto",
                            "--json",
                            "--output",
                            output_path,
                            ".",
                        ],
                        cwd=R,
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )
                    z = json.loads(Path(output_path).read_text(encoding="utf-8"))
                finally:
                    os.unlink(output_path)
                o["summary"]["semgrep"] = {
                    "exit_code": p.returncode,
                    "findings": len(z.get("results", [])),
                    "errors": len(z.get("errors", [])),
                }
            o["status"] = "EXECUTED_NOT_VERIFIED"
            raw = json.dumps(o, sort_keys=True, separators=(",", ":")).encode()
            o["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
            (E / (sid + ".json")).write_bytes(raw)
            self.out(200, o)
        except subprocess.TimeoutExpired:
            self.out(504, {"error": "scanner_timeout"})
        except Exception as e:
            self.out(500, {"error": "scanner_error", "type": type(e).__name__})


ThreadingHTTPServer(("127.0.0.1", 8787), H).serve_forever()
