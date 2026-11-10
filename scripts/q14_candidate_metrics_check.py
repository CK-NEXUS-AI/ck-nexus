from __future__ import annotations

import argparse
import json
import math
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts._safe_http import safe_urlopen_no_redirect
except ImportError:
    from _safe_http import safe_urlopen_no_redirect


def fetch(url: str, token: str = "") -> str:
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with safe_urlopen_no_redirect(request, timeout=5) as response:
        return response.read().decode("utf-8")


def metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        fields = line.split()
        if fields and fields[0] == name:
            if len(fields) != 2:
                raise ValueError(f"candidate metric has an invalid sample: {name}")
            try:
                value = float(fields[1])
            except ValueError as exc:
                raise ValueError(f"candidate metric is not numeric: {name}") from exc
            if not math.isfinite(value):
                raise ValueError(f"candidate metric is not finite: {name}")
            return value
    raise ValueError(f"required candidate metric is missing: {name}")


def validate_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 8000
        or parsed.path not in {"", "/"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit("Q14 base URL must be exactly http://127.0.0.1:8000")
    return "http://127.0.0.1:8000"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--expected-stale-leases", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=Path("q14-candidate-metrics.txt"))
    args = parser.parse_args()

    if not math.isfinite(args.expected_stale_leases) or args.expected_stale_leases < 0:
        raise SystemExit("expected stale-lease count must be finite and non-negative")
    base = validate_base_url(args.base_url)
    health = json.loads(fetch(base + "/health"))
    if health.get("status") != "ok":
        raise SystemExit("candidate health endpoint is not ready")
    metrics = fetch(base + "/metrics", os.getenv("CKNEXUS_ACCESS_TOKEN", ""))
    try:
        stale = metric_value(metrics, "ckn_email_stale_processing_leases")
        pending = metric_value(metrics, "ckn_email_outbox_pending")
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if stale != args.expected_stale_leases:
        raise SystemExit(
            "candidate stale lease metric does not equal the exact injected count: "
            f"expected {args.expected_stale_leases}, got {stale}"
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
