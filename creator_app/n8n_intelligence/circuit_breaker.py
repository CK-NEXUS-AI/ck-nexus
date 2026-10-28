"""Small persistent circuit breaker for upstream n8n API calls."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
import time
from pathlib import Path


class CircuitOpenError(RuntimeError):
    """Raised while the upstream circuit is open."""


class PersistentCircuitBreaker:
    """Persist circuit state across one-shot systemd executions.

    Authentication failures open immediately for a longer cooldown. Repeated
    transient failures open after a bounded threshold. State files are private
    and updates are serialized with an OS file lock.
    """

    def __init__(
        self,
        state_path: Path,
        *,
        failure_threshold: int = 5,
        window_seconds: int = 300,
        transient_cooldown_seconds: int = 120,
        auth_cooldown_seconds: int = 900,
        clock=time.time,
    ) -> None:
        if (
            failure_threshold < 1
            or window_seconds < 1
            or transient_cooldown_seconds < 1
            or auth_cooldown_seconds < 1
        ):
            raise ValueError("circuit breaker bounds must be positive")
        self.state_path = Path(state_path)
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.transient_cooldown_seconds = transient_cooldown_seconds
        self.auth_cooldown_seconds = auth_cooldown_seconds
        self.clock = clock

    def before_request(self) -> None:
        now = self.clock()

        def check(state: dict[str, object]) -> dict[str, object]:
            open_until = float(state.get("open_until", 0))
            if open_until > now:
                raise CircuitOpenError(f"n8n circuit open; retry_after={int(open_until - now)}s")
            # The lock is held during this transition, so only one process can probe.
            if state.get("status") == "open":
                state["status"] = "half_open"
                state["probe_in_flight"] = True
                return state
            if state.get("status") == "half_open" and state.get("probe_in_flight"):
                raise CircuitOpenError("n8n circuit half-open probe already in flight")
            if state.get("status") == "half_open":
                state["probe_in_flight"] = True
            return state

        self._mutate(check)

    def record_success(self) -> None:
        self._mutate(lambda _state: self._closed_state())

    def record_failure(self, *, kind: str) -> None:
        now = self.clock()

        def update(state: dict[str, object]) -> dict[str, object]:
            failures = [
                float(value)
                for value in state.get("failures", [])
                if now - float(value) <= self.window_seconds
            ]
            failures.append(now)
            if kind == "auth":
                return {
                    "status": "open",
                    "failures": failures,
                    "open_until": now + self.auth_cooldown_seconds,
                    "reason": "authentication_failure",
                    "probe_in_flight": False,
                }
            if state.get("status") == "half_open" or len(failures) >= self.failure_threshold:
                return {
                    "status": "open",
                    "failures": failures,
                    "open_until": now + self.transient_cooldown_seconds,
                    "reason": "transient_failure_threshold",
                    "probe_in_flight": False,
                }
            return {
                "status": "closed",
                "failures": failures,
                "open_until": 0,
                "reason": None,
                "probe_in_flight": False,
            }

        self._mutate(update)

    def snapshot(self) -> dict[str, object]:
        state = self._read_locked()
        now = self.clock()
        return {
            "status": state.get("status", "closed"),
            "failure_count": len(state.get("failures", [])),
            "open_for_seconds": max(0, int(float(state.get("open_until", 0)) - now)),
            "reason": state.get("reason"),
        }

    @staticmethod
    def _closed_state() -> dict[str, object]:
        return {
            "status": "closed",
            "failures": [],
            "open_until": 0,
            "reason": None,
            "probe_in_flight": False,
        }

    def _mutate(self, callback) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            state = self._read_unlocked()
            self._write_unlocked(callback(state))
        finally:
            os.close(fd)

    def _read_locked(self) -> dict[str, object]:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            return self._read_unlocked()
        finally:
            os.close(fd)

    def _read_unlocked(self) -> dict[str, object]:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
            state = json.loads(raw)
            if isinstance(state, dict) and isinstance(state.get("failures", []), list):
                return state
        except (OSError, json.JSONDecodeError):
            pass
        return self._closed_state()

    def _write_locked(self, state: dict[str, object]) -> None:
        self._mutate(lambda _old: state)

    def _write_unlocked(self, state: dict[str, object]) -> None:
        fd, temporary = tempfile.mkstemp(prefix=".circuit-", dir=self.state_path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
            os.chmod(self.state_path, 0o600)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary)
