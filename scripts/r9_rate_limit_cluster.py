from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gateway.config import RateLimitPolicy  # noqa: E402
from gateway.rate_limit import RedisTokenBucket  # noqa: E402


async def run(redis_url: str, attempts: int, capacity: int) -> dict[str, object]:
    try:
        limiter_a = RedisTokenBucket.from_url(redis_url, policy_version="r9-evidence")
        limiter_b = RedisTokenBucket.from_url(redis_url, policy_version="r9-evidence")
    except RuntimeError as exc:
        return {"gate": "R9_RATE_LIMIT_CLUSTER", "status": "BLOCKED", "reason": str(exc)}
    policy = RateLimitPolicy("evidence", capacity, 0.000001, fail_closed=True)
    now = int(time.time() * 1000)

    async def attempt(index: int):
        limiter = limiter_a if index % 2 == 0 else limiter_b
        return await limiter.consume("tenant-evidence", "actor-evidence", "route-evidence", policy, now_ms=now)

    try:
        decisions = await asyncio.gather(*(attempt(i) for i in range(attempts)))
    except Exception as exc:
        return {"gate": "R9_RATE_LIMIT_CLUSTER", "status": "BLOCKED", "reason": type(exc).__name__}
    accepted = sum(1 for item in decisions if item.allowed)
    rejected = attempts - accepted
    status = "PASS" if accepted <= capacity and rejected == max(0, attempts - accepted) else "FAIL"
    return {
        "gate": "R9_RATE_LIMIT_CLUSTER",
        "status": status,
        "gateway_instances": 2,
        "policy_capacity": capacity,
        "attempted": attempts,
        "accepted": accepted,
        "rejected": rejected,
        "shared_budget": accepted <= capacity,
        "restart_preserved_budget": "NOT_EXECUTED",
        "redis_failure_policy_verified": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url", default="redis://127.0.0.1:6379/15")
    parser.add_argument("--attempts", type=int, default=140)
    parser.add_argument("--capacity", type=int, default=100)
    args = parser.parse_args()
    result = asyncio.run(run(args.redis_url, args.attempts, args.capacity))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2 if result["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
