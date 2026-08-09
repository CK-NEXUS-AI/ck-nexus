from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creator_app.agnes.execution.phase3 import PostgresIdempotencyStore, RedisIdempotencyStore


def _configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


async def _redis_gate(url: str) -> dict[str, object]:
    try:
        from redis.asyncio import Redis
    except ImportError:
        return {"status": "BLOCKED", "reason": "redis_client_unavailable"}
    client = Redis.from_url(url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5)
    key = "cknexus:gate:agnes:idempotency"
    try:
        await client.delete(key)
        a = RedisIdempotencyStore(client, ttl_seconds=60)
        b = RedisIdempotencyStore(client, ttl_seconds=60)
        first, _ = await a.claim(key, "gate-manifest")
        second, record = await b.claim(key, "gate-manifest")
        await a.complete(key, success=True, result={"gate": "pass"})
        _, replay = await b.claim(key, "gate-manifest")
        passed = bool(
            first is True
            and second is False
            and record is not None
            and replay is not None
            and replay.result == {"gate": "pass"}
        )
        return {"status": "PASS" if passed else "FAIL", "duplicate_blocked": second is False, "replay_verified": bool(replay and replay.result == {"gate": "pass"})}
    except Exception as exc:
        return {"status": "BLOCKED", "reason": f"redis_unreachable:{type(exc).__name__}"}
    finally:
        try:
            await client.delete(key)
            await client.aclose()
        except Exception:
            pass


async def _postgres_gate(url: str) -> dict[str, object]:
    try:
        import asyncpg
    except ImportError:
        return {"status": "BLOCKED", "reason": "asyncpg_client_unavailable"}
    conn: Any = None
    key = "cknexus:gate:agnes:idempotency"
    try:
        conn = await asyncpg.connect(url, timeout=5)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agnes_idempotency (
                idem_key TEXT PRIMARY KEY,
                manifest_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('running','succeeded','failed')),
                result_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute("DELETE FROM agnes_idempotency WHERE idem_key=$1", key)
        store = PostgresIdempotencyStore(conn.execute, conn.fetchrow)
        first, _ = await store.claim(key, "gate-manifest")
        second, record = await store.claim(key, "gate-manifest")
        await store.complete(key, success=True, result={"gate": "pass"})
        _, replay = await store.claim(key, "gate-manifest")
        passed = bool(first and not second and record is not None and replay is not None and replay.result == {"gate": "pass"})
        return {"status": "PASS" if passed else "FAIL", "duplicate_blocked": second is False, "replay_verified": bool(replay and replay.result == {"gate": "pass"})}
    except Exception as exc:
        return {"status": "BLOCKED", "reason": f"postgres_unreachable:{type(exc).__name__}"}
    finally:
        if conn is not None:
            try:
                await conn.execute("DELETE FROM agnes_idempotency WHERE idem_key=$1", key)
            except Exception:
                pass
            await conn.close()


async def main_async(require_live: bool) -> int:
    redis_url = os.getenv("CKNEXUS_AGNES_REDIS_URL", "").strip()
    postgres_url = os.getenv("CKNEXUS_AGNES_POSTGRES_URL", "").strip() or os.getenv("CKNEXUS_DATABASE_URL", "").strip()
    result: dict[str, object] = {
        "gate": "distributed_idempotency",
        "secrets_exposed": False,
        "redis_configured": _configured("CKNEXUS_AGNES_REDIS_URL"),
        "postgres_configured": bool(postgres_url),
    }
    result["redis"] = await _redis_gate(redis_url) if redis_url else {"status": "BLOCKED", "reason": "CKNEXUS_AGNES_REDIS_URL_not_configured"}
    result["postgres"] = await _postgres_gate(postgres_url) if postgres_url else {"status": "BLOCKED", "reason": "postgres_url_not_configured"}
    statuses = {result["redis"]["status"], result["postgres"]["status"]}  # type: ignore[index]
    result["status"] = "PASS" if statuses == {"PASS"} else ("BLOCKED" if "BLOCKED" in statuses else "FAIL")
    print(json.dumps(result, sort_keys=True))
    if require_live and result["status"] != "PASS":
        return 2
    return 0 if result["status"] != "FAIL" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    return asyncio.run(main_async(args.require_live))


if __name__ == "__main__":
    raise SystemExit(main())
