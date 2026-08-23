from __future__ import annotations

import json
import os
from pathlib import Path

from creator_app.credentials.llm_keypool import (
    LlmKeyPool,
    LlmKeySelection,
    LlmKeySpec,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class FreeFallbackKeyPool(LlmKeyPool):
    """LLM key pool with a sticky free-only safety mode.

    Policy:
    - Normal mode behaves exactly like :class:`LlmKeyPool`.
    - When a *paid* provider reports remaining quota <= the configured threshold
      (85% by default), the pool latches into FREE_ONLY mode.
    - In FREE_ONLY mode, paid API keys are never selected.
    - Remote free-tier APIs are disabled by default because third-party free tiers
      can change. They can be explicitly enabled with
      ``CKNEXUS_FREE_ONLY_ALLOW_REMOTE=true``.
    - When no eligible remote free provider exists, ``acquire()`` returns ``None``
      with ``free_fallback=True`` so the caller can route to local Ollama/offline.

    The FREE_ONLY latch is persisted separately from secret/key-pool state and
    contains no credential material.
    """

    DEFAULT_REMAINING_THRESHOLD_PCT = 85.0
    DEFAULT_POLICY_STATE_PATH = "data/free-fallback-policy.json"

    def __init__(
        self,
        specs: list[LlmKeySpec],
        *,
        remaining_threshold_pct: float = DEFAULT_REMAINING_THRESHOLD_PCT,
        sticky_free_only: bool = True,
        allow_remote_free: bool = False,
        policy_state_path: str | None = None,
        **kwargs: object,
    ) -> None:
        if not 0.0 <= remaining_threshold_pct <= 100.0:
            raise ValueError("remaining_threshold_pct must be between 0 and 100")
        self.remaining_threshold_pct = float(remaining_threshold_pct)
        self.sticky_free_only = bool(sticky_free_only)
        self.allow_remote_free = bool(allow_remote_free)
        self.policy_state_path = policy_state_path
        self.free_only_mode = False
        self.free_only_reason: str | None = None
        super().__init__(specs, **kwargs)
        self._load_policy_state()

    @classmethod
    def from_environment(cls) -> FreeFallbackKeyPool | None:
        """Build the guarded pool using the same provider discovery as LlmKeyPool."""
        base = LlmKeyPool.from_environment()
        if base is None:
            return None

        threshold_raw = os.getenv(
            "CKNEXUS_FREE_FALLBACK_REMAINING_PCT",
            str(cls.DEFAULT_REMAINING_THRESHOLD_PCT),
        ).strip()
        try:
            threshold = float(threshold_raw)
        except ValueError as exc:
            raise ValueError("CKNEXUS_FREE_FALLBACK_REMAINING_PCT must be numeric") from exc

        keypool_state_path = os.getenv("CKNEXUS_LLM_STATE_PATH", "").strip() or None
        policy_state_path = (
            os.getenv("CKNEXUS_FREE_FALLBACK_STATE_PATH", "").strip()
            or cls.DEFAULT_POLICY_STATE_PATH
        )

        return cls(
            list(base.specs),
            state_path=keypool_state_path,
            remaining_threshold_pct=threshold,
            sticky_free_only=_env_bool("CKNEXUS_FREE_FALLBACK_STICKY", True),
            allow_remote_free=_env_bool("CKNEXUS_FREE_ONLY_ALLOW_REMOTE", False),
            policy_state_path=policy_state_path,
        )

    def report_quota_usage(
        self, key_id: str, used: int, total: int, *, threshold_pct: float | None = None
    ) -> None:
        """Record quota and latch FREE_ONLY when paid remaining quota reaches the guard."""
        super().report_quota_usage(key_id, used, total, threshold_pct=threshold_pct)
        if total <= 0:
            return

        spec = next((item for item in self.specs if item.id == key_id), None)
        if spec is None or spec.free:
            return

        remaining_pct = max(0.0, min(100.0, ((total - used) / total) * 100.0))
        if remaining_pct <= self.remaining_threshold_pct:
            self.activate_free_only(
                reason=(
                    f"paid provider {key_id} remaining quota {remaining_pct:.2f}% "
                    f"<= guard {self.remaining_threshold_pct:.2f}%"
                )
            )

    def activate_free_only(self, *, reason: str) -> None:
        """Latch the pool into free-only mode without exposing credential material."""
        self.free_only_mode = True
        self.free_only_reason = reason.strip() or "free-only policy activated"
        self.free_fallback = True
        self._save_policy_state()

    def reset_free_only(self) -> None:
        """Explicit operator reset; no automatic reset occurs while sticky mode is enabled."""
        self.free_only_mode = False
        self.free_only_reason = None
        self.free_fallback = False
        self._save_policy_state()

    def acquire(self) -> LlmKeySelection | None:
        if not self.free_only_mode:
            return super().acquire()

        if not self.allow_remote_free:
            self.free_fallback = True
            return None

        now = self._clock()
        self._rotate_pointer(len(self.specs))

        for _ in range(len(self.specs)):
            spec = self.specs[self._pointer]
            api_key = os.getenv(spec.env_var, "").strip()

            if not spec.free or not api_key:
                self._advance_pointer()
                continue
            if self._is_exhausted(spec.id, now) or self._is_in_cooldown(spec.id, now):
                self._advance_pointer()
                continue
            if self._health.get(spec.id) is False:
                self._advance_pointer()
                continue
            if self._is_quota_exhausted(spec.id):
                self._mark_exhausted(spec.id, now + self._exhaustion_recheck)
                self._advance_pointer()
                continue

            self._health[spec.id] = True
            self.free_fallback = False
            selection = LlmKeySelection(
                key_id=spec.id,
                api_key=api_key,
                base_url=spec.base_url,
                model=spec.model,
                provider=spec.id,
                free=True,
            )
            self._save_state()
            return selection

        self.free_fallback = True
        return None

    def policy_status(self) -> dict[str, object]:
        return {
            "mode": "FREE_ONLY" if self.free_only_mode else "NORMAL",
            "free_only": self.free_only_mode,
            "remaining_threshold_pct": self.remaining_threshold_pct,
            "sticky": self.sticky_free_only,
            "allow_remote_free": self.allow_remote_free,
            "local_fallback_required": self.free_only_mode and self.free_fallback,
            "reason": self.free_only_reason,
        }

    def _load_policy_state(self) -> None:
        if not self.policy_state_path:
            return
        path = Path(os.path.expanduser(self.policy_state_path))
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return

        if self.sticky_free_only:
            self.free_only_mode = bool(data.get("free_only_mode", False))
            reason = data.get("reason")
            self.free_only_reason = str(reason) if reason else None
            if self.free_only_mode:
                self.free_fallback = True

    def _save_policy_state(self) -> None:
        if not self.policy_state_path:
            return
        path = Path(os.path.expanduser(self.policy_state_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "cknexus.free-fallback-policy.v1",
            "free_only_mode": self.free_only_mode,
            "remaining_threshold_pct": self.remaining_threshold_pct,
            "sticky": self.sticky_free_only,
            "allow_remote_free": self.allow_remote_free,
            "reason": self.free_only_reason,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
