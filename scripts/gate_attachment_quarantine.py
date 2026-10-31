from __future__ import annotations

import json
import os
import tempfile
import urllib.request
try:
    from scripts._safe_http import safe_urlopen
except ImportError:
    from _safe_http import safe_urlopen
import uuid
import zipfile


def upload(url, path, token):
    boundary = "----ckn" + uuid.uuid4().hex
    data = path.read_bytes()
    name = path.name
    body = (
        (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-CK-NEXUS-Webhook-Token": token,
        },
        method="POST",
    )
    with safe_urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    from pathlib import Path

    base = os.getenv("CKNEXUS_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    token = os.getenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN", "")
    if not token:
        print('{"status":"BLOCKED","reason":"missing webhook token"}')
        return 2
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        exe = d / "evil.exe"
        exe.write_bytes(b"MZ" + b"0" * 32)
        badzip = d / "bomb.zip"
        with zipfile.ZipFile(badzip, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("huge.txt", "A" * 2_000_000)
        safe = d / "safe.txt"
        safe.write_text("hello", encoding="utf-8")
        results = []
        for p, expected in [(exe, False), (badzip, False), (safe, True)]:
            got = upload(base + "/api/email/scan-attachment", p, token)
            actual = bool(got.get("safe"))
            results.append(
                {
                    "file": p.name,
                    "expected_safe": expected,
                    "actual_safe": actual,
                    "reason": got.get("reason"),
                    "pass": actual == expected,
                }
            )
        ok = all(x["pass"] for x in results)
        print(json.dumps({"status": "PASS" if ok else "FAIL", "results": results}, indent=2))
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
