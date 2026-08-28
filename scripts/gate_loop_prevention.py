from __future__ import annotations

import ipaddress
import json
import os
import urllib.request
from urllib.parse import urlsplit


class UnsafeBaseUrl(ValueError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UnsafeBaseUrl("loop-prevention probe refuses HTTP redirects")


def validate_base_url(value: str) -> str:
    raw = value.rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeBaseUrl("base URL must use http/https and include a host")
    host = parsed.hostname.lower()
    if host == "localhost":
        return raw
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise UnsafeBaseUrl("loop-prevention probe is restricted to loopback hosts") from exc
    if not address.is_loopback:
        raise UnsafeBaseUrl("loop-prevention probe is restricted to loopback hosts")
    return raw


def post(url: str, data: object) -> object:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "X-CK-NEXUS-Webhook-Token": os.environ["CKNEXUS_EMAIL_WEBHOOK_TOKEN"],
        },
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    with opener.open(req, timeout=10) as response:
        return json.load(response)


def main() -> int:
    try:
        base = validate_base_url(os.getenv("CKNEXUS_API_BASE", "http://127.0.0.1:8000"))
    except UnsafeBaseUrl as exc:
        print(json.dumps({"status": "BLOCKED", "reason": f"unsafe api base: {exc}"}))
        return 2
    if not os.getenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN"):
        print('{"status":"BLOCKED","reason":"missing webhook token"}')
        return 2
    cases = [
        ({"headers": {"Auto-Submitted": "auto-replied"}, "system_addresses": []}, False),
        ({"headers": {"X-CK-NEXUS-Loop": "evt"}, "system_addresses": []}, False),
        ({"headers": {"Precedence": "bulk"}, "system_addresses": []}, False),
        ({"headers": {"From": "mailer-daemon@example.com"}, "system_addresses": []}, False),
        ({"headers": {"From": "system@example.com"}, "system_addresses": ["system@example.com"]}, False),
        ({"headers": {"From": "human@example.com", "Auto-Submitted": "no"}, "system_addresses": []}, True),
    ]
    results = []
    for payload, expected in cases:
        got = post(base + "/api/email/loop-check", payload)
        actual = bool(got.get("allow_automatic_reply"))
        results.append({"expected": expected, "actual": actual, "pass": actual == expected, "reason": got.get("reason")})
    ok = all(r["pass"] for r in results)
    print(json.dumps({"status": "PASS" if ok else "FAIL", "results": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
