from __future__ import annotations

import asyncio
import math
import re
import time
from dataclasses import dataclass
from typing import Protocol

from .config import RateLimitPolicy
from .errors import GatewayError

_SAFE_FRAGMENT = re.compile(r"[^A-Za-z0-9_.:-]+")


def safe_fragment(value: str, *, limit: int = 96) -> str:
    cleaned = _SAFE_FRAGMENT.sub("_", value.strip())[:limit]
    return cleaned or "_"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class EvalBackend(Protocol):
    async def eval(self, script: str, numkeys: int, *args: object) -> object: ...


TOKEN_BUCKET_LUA = r'''
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_ms = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl_ms = tonumber(ARGV[5])

local values = redis.call('HMGET', key, 'tokens', 'last_ms')
local tokens = tonumber(values[1])
local last_ms = tonumber(values[2])
if tokens == nil then tokens = capacity end
if last_ms == nil then last_ms = now_ms end

local elapsed = math.max(0, now_ms - last_ms)
local refilled = math.min(capacity, tokens + elapsed * refill_per_ms)
local allowed = 0
if refilled >= requested then
  allowed = 1
  refilled = refilled - requested
end
redis.call('HSET', key, 'tokens', refilled, 'last_ms', now_ms)
redis.call('PEXPIRE', key, ttl_ms)
local missing = math.max(0, requested - refilled)
local retry_ms = 0
if allowed == 0 and refill_per_ms > 0 then
  retry_ms = math.ceil(missing / refill_per_ms)
end
return {allowed, math.floor(refilled), retry_ms}
'''


class RedisTokenBucket:
    def __init__(self, backend: EvalBackend, *, policy_version: str) -> None:
        self._backend = backend
        self._policy_version = safe_fragment(policy_version)

    @classmethod
    def from_url(cls, redis_url: str, *, policy_version: str) -> RedisTokenBucket:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise RuntimeError("redis package is required for gateway Redis rate limiting") from exc
        return cls(aioredis.from_url(redis_url, decode_responses=True), policy_version=policy_version)

    async def ping(self) -> bool:
        try:
            ping = self._backend.ping
            return bool(await ping())
        except Exception:
            return False

    def key(self, tenant_id: str, actor_id: str, route_id: str) -> str:
        return f"ratelimit:{self._policy_version}:{safe_fragment(tenant_id)}:{safe_fragment(actor_id)}:{safe_fragment(route_id)}"

    async def consume(
        self,
        tenant_id: str,
        actor_id: str,
        route_id: str,
        policy: RateLimitPolicy,
        *,
        requested_tokens: int = 1,
        now_ms: int | None = None,
    ) -> RateLimitDecision:
        timestamp = int(time.time() * 1000) if now_ms is None else now_ms
        ttl_ms = max(1_000, int(math.ceil(policy.capacity / policy.refill_per_second * 2_000)))
        try:
            raw = await self._backend.eval(
                TOKEN_BUCKET_LUA,
                1,
                self.key(tenant_id, actor_id, route_id),
                policy.capacity,
                policy.refill_per_second / 1000.0,
                timestamp,
                requested_tokens,
                ttl_ms,
            )
            allowed, remaining, retry_ms = [int(float(item)) for item in raw]
        except Exception:
            if policy.fail_closed:
                raise GatewayError(
                    "RATE_LIMIT_UNAVAILABLE",
                    "Request policy service is unavailable.",
                    503,
                    retryable=True,
                ) from None
            return RateLimitDecision(True, policy.capacity, 0)
        return RateLimitDecision(bool(allowed), remaining, max(0, math.ceil(retry_ms / 1000)))


@dataclass(slots=True)
class _MemoryBucket:
    tokens: float
    last_ms: int


class InMemoryTokenBucket:
    """Deterministic test/local backend. Never selected automatically in production."""

    def __init__(self, *, policy_version: str, shared_state: dict[str, _MemoryBucket] | None = None) -> None:
        self.policy_version = safe_fragment(policy_version)
        self._state = shared_state if shared_state is not None else {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    def key(self, tenant_id: str, actor_id: str, route_id: str) -> str:
        return f"ratelimit:{self.policy_version}:{safe_fragment(tenant_id)}:{safe_fragment(actor_id)}:{safe_fragment(route_id)}"

    async def consume(
        self,
        tenant_id: str,
        actor_id: str,
        route_id: str,
        policy: RateLimitPolicy,
        *,
        requested_tokens: int = 1,
        now_ms: int | None = None,
    ) -> RateLimitDecision:
        timestamp = int(time.time() * 1000) if now_ms is None else now_ms
        key = self.key(tenant_id, actor_id, route_id)
        async with self._lock:
            bucket = self._state.get(key) or _MemoryBucket(float(policy.capacity), timestamp)
            elapsed = max(0, timestamp - bucket.last_ms)
            tokens = min(policy.capacity, bucket.tokens + elapsed * policy.refill_per_second / 1000.0)
            if tokens < requested_tokens:
                missing = requested_tokens - tokens
                retry = math.ceil(missing / policy.refill_per_second)
                self._state[key] = _MemoryBucket(tokens, timestamp)
                return RateLimitDecision(False, math.floor(tokens), max(1, retry))
            tokens -= requested_tokens
            self._state[key] = _MemoryBucket(tokens, timestamp)
            return RateLimitDecision(True, math.floor(tokens), 0)
