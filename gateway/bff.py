from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


async def bounded_fanout(
    calls: dict[str, Callable[[], Awaitable[object]]],
    *,
    max_parallelism: int = 4,
) -> dict[str, dict[str, object]]:
    if max_parallelism < 1:
        raise ValueError("max_parallelism must be >= 1")
    semaphore = asyncio.Semaphore(max_parallelism)

    async def run(
        name: str, call: Callable[[], Awaitable[object]]
    ) -> tuple[str, dict[str, object]]:
        async with semaphore:
            try:
                value = await call()
                return name, {"status": "ok", "data": value}
            except Exception:
                return name, {"status": "degraded", "data": None}

    results = await asyncio.gather(*(run(name, call) for name, call in calls.items()))
    return dict(results)
