from __future__ import annotations

import argparse
import ipaddress
import os
import urllib.request
from urllib.parse import urlsplit


class UnsafeBaseUrl(ValueError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UnsafeBaseUrl("observability probe refuses HTTP redirects")


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
        raise UnsafeBaseUrl("observability probe is restricted to loopback hosts") from exc
    if not address.is_loopback:
        raise UnsafeBaseUrl("observability probe is restricted to loopback hosts")
    return raw


def fetch(url: str, *, token: str = "") -> str:
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    opener = urllib.request.build_opener(NoRedirectHandler())
    with opener.open(request, timeout=5) as response:
        return response.read().decode("utf-8")


def metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split()[-1])
    return 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-outbox-pending", type=int, default=100)
    args = parser.parse_args()

    try:
        base_url = validate_base_url(args.base_url)
    except UnsafeBaseUrl as exc:
        print(f"P0-OBS-001 BLOCKED unsafe_base_url: {exc}")
        return 2

    health = fetch(base_url + "/health")
    if '"status":"ok"' not in health.replace(" ", ""):
        print("P0-OBS-001 FAIL health")
        return 1
    metrics = fetch(base_url + "/metrics", token=os.getenv("CKNEXUS_ACCESS_TOKEN", ""))
    pending = metric_value(metrics, "ckn_email_outbox_pending")
    stale = metric_value(metrics, "ckn_email_stale_processing_leases")
    if pending > args.max_outbox_pending or stale > 0:
        print(f"P0-OBS-001 ALERT pending={pending} stale_leases={stale}")
        return 1
    print(f"P0-OBS-001 CHECK PASS pending={pending} stale_leases={stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
