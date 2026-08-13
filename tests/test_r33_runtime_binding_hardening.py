import asyncio
from types import SimpleNamespace

import pytest

from creator_app import runtime_binding as rb


def cfg(**overrides):
    values = dict(
        database_url="postgresql://user:pass@127.0.0.1:5432/db",
        redis_url="redis://127.0.0.1:6379/0",
        db_connect_timeout=0.01,
        db_command_timeout=0.01,
        db_pool_acquire_timeout=0.01,
        redis_connect_timeout=0.01,
        redis_socket_timeout=0.01,
    )
    values.update(overrides)
    c = rb.RuntimeBindingConfig(**values)
    c.validate()
    return c


def test_timeout_contract_rejects_nonpositive_values():
    for field in (
        "db_connect_timeout",
        "db_command_timeout",
        "db_pool_acquire_timeout",
        "redis_connect_timeout",
        "redis_socket_timeout",
    ):
        with pytest.raises(RuntimeError):
            cfg(**{field: 0})


@pytest.mark.asyncio
async def test_db_pool_connect_is_bounded(monkeypatch):
    async def slow_create_pool(**kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr(rb, "_db_pool", None)
    monkeypatch.setattr(rb, "asyncpg", SimpleNamespace(create_pool=slow_create_pool))
    with pytest.raises(asyncio.TimeoutError):
        await rb.get_db_pool(cfg())


@pytest.mark.asyncio
async def test_db_pool_acquire_is_bounded():
    class Pool:
        async def acquire(self):
            await asyncio.sleep(1)
        async def release(self, conn):
            pass

    with pytest.raises(asyncio.TimeoutError):
        async with rb.acquire_db_connection(Pool(), cfg()):
            pass


def test_missing_asyncpg_fails_closed(monkeypatch):
    monkeypatch.setattr(rb, "_db_pool", None)
    monkeypatch.setattr(rb, "asyncpg", None)
    with pytest.raises(RuntimeError, match="asyncpg"):
        asyncio.run(rb.get_db_pool(cfg()))


def test_missing_redis_fails_closed(monkeypatch):
    monkeypatch.setattr(rb, "_redis_client", None)
    monkeypatch.setattr(rb, "redis", None)
    with pytest.raises(RuntimeError, match="redis"):
        asyncio.run(rb.get_redis_client(cfg()))
