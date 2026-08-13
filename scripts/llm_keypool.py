#!/usr/bin/env python3
"""CK-NEXUS LLM key pool CLI: probe health/credit and inspect rotation state.

Usage:
  python scripts/llm_keypool.py status [--json]
  python scripts/llm_keypool.py probe [--json]

Exit codes:
  0  at least one key is healthy
  1  keys configured but none healthy
  2  no LLM keys configured
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creator_app.llm_keypool import LlmKeyPool


def _emit(pool: LlmKeyPool, as_json: bool, healthy: bool) -> int:
    statuses = pool.status()
    if as_json:
        print(
            json.dumps(
                {
                    "keys": [
                        {
                            "id": item.key_id,
                            "provider": item.provider,
                            "model": item.model,
                            "free": item.free,
                            "healthy": item.healthy,
                            "cooldown_until": item.cooldown_until,
                            "consecutive_failures": item.consecutive_failures,
                            "exhausted": item.exhausted,
                            "source": item.source,
                        }
                        for item in statuses
                    ],
                    "free_fallback": pool.free_fallback,
                },
                indent=2,
            )
        )
        return 0 if healthy else 1
    header = (
        f"{'ID':<14} {'PROVIDER':<14} {'MODEL':<42} {'FREE':<5} {'HEALTHY':<8} "
        f"{'COOLDOWN':<12} {'FAILS':<6} {'SRC'}"
    )
    print(header)
    for item in statuses:
        cooldown = f"{item.cooldown_until:.1f}" if item.cooldown_until else "-"
        print(
            f"{item.key_id:<14} {item.provider:<14} {item.model:<42} "
            f"{'yes' if item.free else 'no':<5} {str(item.healthy):<8} {cooldown:<12} "
            f"{item.consecutive_failures:<6} {item.source}"
        )
    print(
        f"\nfree_fallback={pool.free_fallback}  "
        "(true = all keys unavailable; use local/free mode)"
    )
    return 0 if healthy else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "probe"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    try:
        pool = LlmKeyPool.from_environment()
    except ValueError as exc:
        print(f"[keypool] configuration error: {exc}", file=sys.stderr)
        return 2
    if pool is None:
        print(
            "[keypool] No LLM keys configured. Set CKNEXUS_LLM_KEYS (JSON list) or any "
            "provider env var (GROQ_API_KEY, MISTRAL_API_KEY, GEMINI_API_KEY, "
            "MOONSHOT_API_KEY, ...).",
            file=sys.stderr,
        )
        return 2

    if args.command == "probe":
        pool.probe_all()
    healthy = any(item.healthy for item in pool.status())
    return _emit(pool, args.json, healthy)


if __name__ == "__main__":
    raise SystemExit(main())
