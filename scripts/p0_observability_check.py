from __future__ import annotations

import argparse
import os
import urllib.request

try:
    from scripts._safe_http import safe_urlopen
except ImportError:
    from _safe_http import safe_urlopen


def fetch(url: str, *, token: str = "") -> str:
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with safe_urlopen(request, timeout=5) as response:
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

    health = fetch(args.base_url.rstrip("/") + "/health")
    if '"status":"ok"' not in health.replace(" ", ""):
        print("P0-OBS-001 FAIL health")
        return 1
    metrics = fetch(
        args.base_url.rstrip("/") + "/metrics", token=os.getenv("CKNEXUS_ACCESS_TOKEN", "")
    )
    pending = metric_value(metrics, "ckn_email_outbox_pending")
    stale = metric_value(metrics, "ckn_email_stale_processing_leases")
    if pending > args.max_outbox_pending or stale > 0:
        print(f"P0-OBS-001 ALERT pending={pending} stale_leases={stale}")
        return 1
    print(f"P0-OBS-001 CHECK PASS pending={pending} stale_leases={stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
