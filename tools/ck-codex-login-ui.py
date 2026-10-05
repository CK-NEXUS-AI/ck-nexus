#!/usr/bin/env python3
"""Local-only clickable UI for CK-Codex Account Switcher.

Security model:
- binds only to 127.0.0.1
- never accepts or relays credentials, passwords, OTPs, API keys, device codes, or tokens
- delegates authentication to official Codex CLI device auth
- only allows validated local profile names
"""
from __future__ import annotations

import http.server
import os
import re
import subprocess
import threading
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWITCHER = ROOT / "tools" / "ck-codex-account.py"
HOST, PORT = "127.0.0.1", 8765
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HTML = (ROOT / "plugins" / "ck-codex-account-switcher" / "login-ui.html").read_text(encoding="utf-8")
BASE = os.environ.get("CK_CODEX_ACCOUNTS_HOME", str(Path.home() / ".ck-codex-accounts"))


def valid(name: str) -> bool:
    return bool(NAME_RE.fullmatch(name))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CK_CODEX_ACCOUNTS_HOME"] = BASE
    return subprocess.run(
        ["python3", str(SWITCHER), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def login(profile: str) -> str:
    if not valid(profile):
        return "Invalid profile name."
    add = run("add", profile)
    if add.returncode != 0:
        # Existing profiles are fine; only reject unexpected add failures.
        if "already exists" not in (add.stderr + add.stdout):
            return (add.stdout + add.stderr).strip()

    # Keep the official device-auth process attached to the launching terminal.
    # The browser UI must never capture, return, store, or display device codes.
    subprocess.Popen(
        ["python3", str(SWITCHER), "login", profile],
        env={**os.environ, "CK_CODEX_ACCOUNTS_HOME": BASE},
    )
    return (
        "Official Codex device login started. "
        "Complete authentication in the official OpenAI flow/terminal; "
        "this UI does not handle or display device codes. Then click Check status."
    )


class Handler(http.server.BaseHTTPRequestHandler):
    def send(self, code: int, body: str, ctype="text/plain; charset=utf-8"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            return self.send(200, HTML, "text/html; charset=utf-8")
        if u.path == "/status":
            p = q.get("profile", [""])[0]
            if not valid(p):
                return self.send(400, "Invalid profile name.")
            r = run("status", p)
            return self.send(200, (r.stdout + r.stderr).strip())
        return self.send(404, "Not found.")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/login":
            p = q.get("profile", [""])[0]
            return self.send(200, login(p))
        return self.send(404, "Not found.")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"CK-Codex Login UI: http://{HOST}:{PORT}")
    print("Local-only: 127.0.0.1; stop with Ctrl-C.")
    threading.Timer(0.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}/")).start()
    server.serve_forever()
