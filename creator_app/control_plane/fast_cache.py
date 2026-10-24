"""Short-lived cache for explicitly read-only control-plane observations."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class _Entry:
    expires_at: float
    value: Any


class ReadOnlyTTLCache:
    def __init__(
        self, ttl_seconds: float = 5.0, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, _Entry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._clock() >= entry.expires_at:
            self._entries.pop(key, None)
            return None
        return entry.value

    def put(self, key: str, value: Any, *, cacheable: bool = True) -> None:
        if not cacheable:
            self._entries.pop(key, None)
            return
        self._entries[key] = _Entry(self._clock() + self.ttl_seconds, value)

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()
