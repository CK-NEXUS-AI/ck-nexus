from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from ..idempotency import IdempotencyRecord, IdempotencyState


class RedisIdempotencyStore:
    """Distributed Redis adapter. Requires a redis-py compatible async client."""

    durable = True
    distributed = True
    production_safe = True

    def __init__(self, client: Any, *, ttl_seconds: int = 86400) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    async def claim(self, key: str, manifest_hash: str) -> tuple[bool, IdempotencyRecord | None]:
        payload = json.dumps({"manifest_hash": manifest_hash, "state": "running", "result": None}, sort_keys=True)
        created = await self.client.set(key, payload, nx=True, ex=self.ttl_seconds)
        if created:
            return True, IdempotencyRecord(manifest_hash, IdempotencyState.RUNNING)
        raw = await self.client.get(key)
        if raw is None:
            return False, None
        if isinstance(raw, bytes):
            raw = raw.decode()
        data = json.loads(raw)
        return False, IdempotencyRecord(
            data["manifest_hash"], IdempotencyState(data["state"]), data.get("result")
        )

    async def complete(self, key: str, *, success: bool, result: dict[str, object]) -> None:
        raw = await self.client.get(key)
        if raw is None:
            return
        if isinstance(raw, bytes):
            raw = raw.decode()
        data = json.loads(raw)
        data["state"] = "succeeded" if success else "failed"
        data["result"] = result
        await self.client.set(key, json.dumps(data, sort_keys=True), xx=True, ex=self.ttl_seconds)


class PostgresIdempotencyStore:
    """Distributed PostgreSQL adapter using caller-supplied async execute/fetch functions.

    The adapter deliberately avoids binding CK-NEXUS to a specific driver. `execute` and
    `fetchrow` can be backed by asyncpg/SQLAlchemy wrappers in staging.
    """

    durable = True
    distributed = True
    production_safe = True

    def __init__(self, execute: Callable[..., Any], fetchrow: Callable[..., Any]) -> None:
        self._execute = execute
        self._fetchrow = fetchrow

    async def claim(self, key: str, manifest_hash: str) -> tuple[bool, IdempotencyRecord | None]:
        inserted = await self._fetchrow(
            """
            INSERT INTO agnes_idempotency(idem_key, manifest_hash, state)
            VALUES($1,$2,'running') ON CONFLICT (idem_key) DO NOTHING
            RETURNING manifest_hash, state, result_json
            """,
            key,
            manifest_hash,
        )
        if inserted:
            return True, IdempotencyRecord(manifest_hash, IdempotencyState.RUNNING)
        row = await self._fetchrow(
            "SELECT manifest_hash, state, result_json FROM agnes_idempotency WHERE idem_key=$1",
            key,
        )
        if not row:
            return False, None
        result = row["result_json"]
        if isinstance(result, str):
            result = json.loads(result)
        return False, IdempotencyRecord(str(row["manifest_hash"]), IdempotencyState(str(row["state"])), result)

    async def complete(self, key: str, *, success: bool, result: dict[str, object]) -> None:
        await self._execute(
            "UPDATE agnes_idempotency SET state=$2, result_json=$3 WHERE idem_key=$1",
            key,
            "succeeded" if success else "failed",
            json.dumps(result, sort_keys=True, separators=(",", ":")),
        )
