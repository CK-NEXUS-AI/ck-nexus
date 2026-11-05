from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

try:
    from scripts._safe_http import safe_urlopen
except ImportError:
    from _safe_http import safe_urlopen


def fetch(url: str, token: str = "") -> str:
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with safe_urlopen(request, timeout=5) as response:
        return response.read().decode("utf-8")


def metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split()[-1])
    raise ValueError(f"required candidate metric is missing: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--expected-stale-leases", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=Path("q14-candidate-metrics.txt"))
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    health = json.loads(fetch(base + "/health"))
    if health.get("status") != "ok":
        raise SystemExit("candidate health endpoint is not ready")
    metrics = fetch(base + "/metrics", os.getenv("CKNEXUS_ACCESS_TOKEN", ""))
    try:
        stale = metric_value(metrics, "ckn_email_stale_processing_leases")
        pending = metric_value(metrics, "ckn_email_outbox_pending")
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if stale < args.expected_stale_leases:
        raise SystemExit(
            f"candidate stale lease metric below injected threshold: {stale}"
        )
    args.output.write_text(metrics, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "health": "PASS",
                "metrics_source": "CK-NEXUS /metrics",
                "stale_processing_leases": stale,
                "expected_stale_processing_leases": args.expected_stale_leases,
                "outbox_pending": pending,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
