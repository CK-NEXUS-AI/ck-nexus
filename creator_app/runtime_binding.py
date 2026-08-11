"""CK-NEXUS Runtime Binding Module.

Provides application-level PostgreSQL and Redis bindings plus an evidence-first
CLI verifier that keeps CONNECTIVITY separate from APPLICATION_BINDING.

Usage:
    python runtime_binding.py --verify
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore[assignment]


@dataclass(frozen=True)
class RuntimeBindingConfig:
    database_url: str
    redis_url: str
    db_pool_min: int = 1
    db_pool_max: int = 5
    redis_socket_timeout: float = 5.0
    redis_max_connections: int = 10
    fail_fast: bool = True

    @classmethod
    def from_env(cls) -> "RuntimeBindingConfig":
        database_url = os.environ.get("DATABASE_URL", "").strip()
        redis_url = os.environ.get("REDIS_URL", "").strip()

        if not database_url:
            raise RuntimeError("DATABASE_URL is not set — runtime cannot bind to PostgreSQL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is not set — runtime cannot bind to Redis")

        cfg = cls(
            database_url=database_url,
            redis_url=redis_url,
            db_pool_min=int(os.environ.get("DB_POOL_MIN", "1")),
            db_pool_max=int(os.environ.get("DB_POOL_MAX", "5")),
            redis_socket_timeout=float(os.environ.get("REDIS_SOCKET_TIMEOUT", "5")),
            redis_max_connections=int(os.environ.get("REDIS_MAX_CONNECTIONS", "10")),
            fail_fast=os.environ.get("RUNTIME_BINDING_FAIL_FAST", "true").strip().lower()
            in {"1", "true", "yes", "on"},
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.db_pool_min < 1:
            raise RuntimeError("DB_POOL_MIN must be >= 1")
        if self.db_pool_max < self.db_pool_min:
            raise RuntimeError("DB_POOL_MAX must be >= DB_POOL_MIN")
        if self.redis_socket_timeout <= 0:
            raise RuntimeError("REDIS_SOCKET_TIMEOUT must be > 0")
        if self.redis_max_connections < 1:
            raise RuntimeError("REDIS_MAX_CONNECTIONS must be >= 1")


_db_pool: Optional[Any] = None
_redis_client: Optional[Any] = None


def _safe_error(exc: BaseException) -> str:
    """Return a conservative error summary without echoing DSNs or credentials."""
    return f"{type(exc).__name__}: connection/binding operation failed"


async def get_db_pool(cfg: Optional[RuntimeBindingConfig] = None):
    global _db_pool
    if asyncpg is None:
        raise RuntimeError("asyncpg is not installed")
    if _db_pool is None:
        cfg = cfg or RuntimeBindingConfig.from_env()
        _db_pool = await asyncpg.create_pool(
            dsn=cfg.database_url,
            min_size=cfg.db_pool_min,
            max_size=cfg.db_pool_max,
        )
    return _db_pool


async def get_redis_client(cfg: Optional[RuntimeBindingConfig] = None):
    global _redis_client
    if redis is None:
        raise RuntimeError("redis package is not installed")
    if _redis_client is None:
        cfg = cfg or RuntimeBindingConfig.from_env()
        _redis_client = redis.from_url(
            cfg.redis_url,
            socket_timeout=cfg.redis_socket_timeout,
            max_connections=cfg.redis_max_connections,
            decode_responses=True,
        )
    return _redis_client


async def close_all() -> None:
    global _db_pool, _redis_client

    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None




async def runtime_binding_status() -> dict[str, bool]:
    """Return secret-free app-level binding state using the shared pool/client."""
    db_ok = False
    redis_ok = False
    if _db_pool is not None:
        try:
            async with _db_pool.acquire() as conn:
                db_ok = (await conn.fetchval("SELECT 1")) == 1
        except Exception:
            db_ok = False
    if _redis_client is not None:
        try:
            redis_ok = bool(await _redis_client.ping())
        except Exception:
            redis_ok = False
    return {"postgres": db_ok, "redis": redis_ok}


async def verify_runtime_binding_or_raise() -> None:
    """Application startup gate.

    If fail-fast is enabled, startup fails unless both app-level bindings work.
    If disabled, failures are reported as degraded-mode warnings.
    """
    cfg = RuntimeBindingConfig.from_env()
    errors: list[str] = []

    try:
        try:
            pool = await get_db_pool(cfg)
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
            if result != 1:
                raise RuntimeError("unexpected PostgreSQL health-query result")
        except Exception as exc:  # startup boundary
            errors.append(f"PostgreSQL application binding failed: {_safe_error(exc)}")

        try:
            client = await get_redis_client(cfg)
            pong = await client.ping()
            if not pong:
                raise RuntimeError("Redis PING returned a false value")
        except Exception as exc:  # startup boundary
            errors.append(f"Redis application binding failed: {_safe_error(exc)}")

        if errors and cfg.fail_fast:
            raise RuntimeError(
                "RUNTIME_BINDING_FAIL_FAST=true and binding failed:\n" + "\n".join(errors)
            )

        for error in errors:
            print(f"[WARNING][degraded-mode] {error}", file=sys.stderr)
    except Exception:
        # Prevent half-open resources after a failed startup attempt.
        await close_all()
        raise


async def _verify_postgres_connectivity(cfg: RuntimeBindingConfig) -> dict[str, str]:
    if asyncpg is None:
        return {
            "level": "CONNECTIVITY",
            "status": "BLOCKED",
            "detail": "asyncpg not installed",
        }

    conn = None
    try:
        conn = await asyncpg.connect(dsn=cfg.database_url, timeout=5)
        version = await conn.fetchval("SELECT version()")
        return {
            "level": "CONNECTIVITY",
            "status": "PASS",
            "detail": str(version),
        }
    except Exception as exc:
        return {
            "level": "CONNECTIVITY",
            "status": "FAIL",
            "detail": _safe_error(exc),
        }
    finally:
        if conn is not None:
            await conn.close()


async def _verify_postgres_application_binding(
    cfg: RuntimeBindingConfig,
) -> dict[str, str]:
    try:
        pool = await get_db_pool(cfg)
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
        return {
            "level": "APPLICATION_BINDING",
            "status": "PASS" if result == 1 else "FAIL",
            "detail": f"pool acquire + query ok (min={cfg.db_pool_min}, max={cfg.db_pool_max})",
        }
    except Exception as exc:
        return {
            "level": "APPLICATION_BINDING",
            "status": "FAIL",
            "detail": _safe_error(exc),
        }


async def _verify_redis_connectivity(cfg: RuntimeBindingConfig) -> dict[str, str]:
    if redis is None:
        return {
            "level": "CONNECTIVITY",
            "status": "BLOCKED",
            "detail": "redis package not installed",
        }

    client = None
    try:
        client = redis.from_url(
            cfg.redis_url,
            socket_timeout=cfg.redis_socket_timeout,
            decode_responses=True,
        )
        pong = await client.ping()
        return {
            "level": "CONNECTIVITY",
            "status": "PASS" if pong else "FAIL",
            "detail": f"PING -> {pong}",
        }
    except Exception as exc:
        return {
            "level": "CONNECTIVITY",
            "status": "FAIL",
            "detail": _safe_error(exc),
        }
    finally:
        if client is not None:
            await client.aclose()


async def _verify_redis_application_binding(
    cfg: RuntimeBindingConfig,
) -> dict[str, str]:
    key = f"ck-nexus:runtime-binding-check:{uuid.uuid4().hex}"
    client = None
    try:
        client = await get_redis_client(cfg)
        marker = f"{time.time_ns()}:{uuid.uuid4().hex}"
        await client.set(key, marker, ex=30)
        readback = await client.get(key)
        ok = readback == marker
        return {
            "level": "APPLICATION_BINDING",
            "status": "PASS" if ok else "FAIL",
            "detail": f"set/get round-trip {'matched' if ok else 'MISMATCH'}",
        }
    except Exception as exc:
        return {
            "level": "APPLICATION_BINDING",
            "status": "FAIL",
            "detail": _safe_error(exc),
        }
    finally:
        if client is not None:
            try:
                await client.delete(key)
            except Exception:
                pass


async def run_verification() -> bool:
    print("=" * 60)
    print("CK-NEXUS Runtime Binding Verification (evidence-first)")
    print("=" * 60)

    try:
        cfg = RuntimeBindingConfig.from_env()
    except Exception as exc:
        print(f"[BLOCKED] {_safe_error(exc) if not isinstance(exc, RuntimeError) else exc}")
        print("\n>> Set DATABASE_URL / REDIS_URL first (see .env.runtime-binding.example)")
        return False

    checks = [
        (
            "PostgreSQL",
            _verify_postgres_connectivity,
            _verify_postgres_application_binding,
        ),
        ("Redis", _verify_redis_connectivity, _verify_redis_application_binding),
    ]

    overall_pass = True
    try:
        for name, connectivity_fn, binding_fn in checks:
            print(f"\n--- {name} ---")
            conn_result = await connectivity_fn(cfg)
            print(
                f"  [{conn_result['status']:7s}] CONNECTIVITY       : {conn_result['detail']}"
            )

            if conn_result["status"] != "PASS":
                print(
                    "  [SKIPPED] APPLICATION_BINDING : connectivity failed/blocked; app-level check not counted"
                )
                overall_pass = False
                continue

            bind_result = await binding_fn(cfg)
            print(
                f"  [{bind_result['status']:7s}] APPLICATION_BINDING: {bind_result['detail']}"
            )
            if bind_result["status"] != "PASS":
                overall_pass = False
    finally:
        await close_all()

    print("\n" + "=" * 60)
    print(
        "OVERALL: "
        + (
            "PASS — runtime is bound, not just reachable"
            if overall_pass
            else "FAIL/BLOCKED — see evidence above"
        )
    )
    print("=" * 60)
    return overall_pass


def main() -> int:
    if "--verify" not in sys.argv:
        print("Usage: python runtime_binding.py --verify")
        print(
            "Or import get_db_pool / get_redis_client / verify_runtime_binding_or_raise in CK-NEXUS app"
        )
        return 2

    passed = asyncio.run(run_verification())
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
