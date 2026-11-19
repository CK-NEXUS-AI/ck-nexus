from __future__ import annotations

from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic


class SlidingWindowRateLimiter:
    """Small in-process limiter suitable for a single-user or single-worker MVP."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> int:
        """Return zero when allowed, otherwise seconds until the next request."""
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                return max(1, ceil(self.window_seconds - (now - timestamps[0])))
            timestamps.append(now)
            return 0
