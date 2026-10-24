"""Bounded concurrent read-only probes for the fast control path."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProbeResult:
    status: str
    elapsed_ms: float
    error: str | None = None


Probe = Callable[[], Awaitable[Any] | Any]


class FastProbeRunner:
    def __init__(self, max_concurrency: int = 2) -> None:
        if max_concurrency < 1 or max_concurrency > 3:
            raise ValueError("max_concurrency must be between 1 and 3")
        self.max_concurrency = max_concurrency

    async def run(self, probes: dict[str, Probe]) -> dict[str, ProbeResult]:
        if not probes:
            return {}
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute(probe: Probe) -> ProbeResult:
            async with semaphore:
                started = time.monotonic()
                try:
                    value = probe()
                    if hasattr(value, "__await__"):
                        await value
                    return ProbeResult("ok", (time.monotonic() - started) * 1000)
                except Exception as exc:  # noqa: BLE001 - boundary returns redacted type only
                    return ProbeResult(
                        "error", (time.monotonic() - started) * 1000, type(exc).__name__
                    )

        names = tuple(probes)
        results = await asyncio.gather(*(execute(probes[name]) for name in names))
        return dict(zip(names, results, strict=True))
