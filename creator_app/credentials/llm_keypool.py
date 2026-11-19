from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol
from urllib.parse import urlparse

from creator_app.credentials.free_providers import AUTO_DISCOVER_PROVIDERS


class KeyPoolError(RuntimeError):
    """Raised for key pool misconfiguration. Never carries secret material."""


@dataclass(frozen=True, slots=True)
class LlmKeySpec:
    """Declarative spec for one LLM API key. The secret itself lives in an env var."""

    id: str
    env_var: str
    base_url: str
    model: str
    free: bool = False

    @classmethod
    def from_mapping(cls, raw: dict) -> LlmKeySpec:
        required = ("id", "env_var", "base_url", "model")
        missing = [key for key in required if not str(raw.get(key, "")).strip()]
        if missing:
            raise KeyPoolError(f"llm key spec missing required fields: {', '.join(missing)}")
        return cls(
            id=str(raw["id"]).strip(),
            env_var=str(raw["env_var"]).strip(),
            base_url=str(raw["base_url"]).strip().rstrip("/"),
            model=str(raw["model"]).strip(),
            free=bool(raw.get("free", False)),
        )


@dataclass(frozen=True, slots=True)
class LlmKeySelection:
    """Resolved credential for one run. `api_key` is a secret and must never be logged."""

    key_id: str
    api_key: str
    base_url: str
    model: str
    provider: str
    free: bool

    def __repr__(self) -> str:
        return (
            f"LlmKeySelection(key_id={self.key_id!r}, provider={self.provider!r}, "
            f"model={self.model!r}, api_key=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class LlmKeyStatus:
    key_id: str
    provider: str
    model: str
    free: bool
    healthy: bool | None
    cooldown_until: float
    consecutive_failures: int
    exhausted: bool
    source: str
    quota_percentage_used: float | None = None


@dataclass(slots=True)
class ProbeResult:
    status: int | None
    ok: bool
    detail: str


class KeyProber(Protocol):
    def probe(self, spec: LlmKeySpec, api_key: str, *, timeout: float) -> ProbeResult: ...


class HttpKeyProber:
    """Probes an OpenAI-compatible /models endpoint with a bounded timeout.

    200/401/403/404 responses are authoritative for credential validity;
    network errors are reported as degraded so the pool can retry later.
    """

    def __init__(self, *, open_url: Callable[..., object] | None = None) -> None:
        self._open_url = open_url or urllib.request.urlopen

    def probe(self, spec: LlmKeySpec, api_key: str, *, timeout: float) -> ProbeResult:
        url = f"{spec.base_url}/models"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        try:
            with self._open_url(request, timeout=timeout) as response:
                return ProbeResult(
                    status=getattr(response, "status", 200), ok=True, detail="reachable"
                )
        except urllib.error.HTTPError as exc:
            return ProbeResult(status=exc.code, ok=False, detail=f"http_{exc.code}")
        except Exception as exc:  # URLError, timeout, TLS, DNS
            return ProbeResult(status=None, ok=False, detail=type(exc).__name__)


class LlmKeyPool:
    """Health-checked LLM API key pool with rotation, cooldowns, and free fallback.

    Design follows the patterns used by llm-keypool / poolctl / LiteLLM routers:

    * Cheap ``GET /models`` probe classifies a key as healthy / unauthorized / degraded.
    * ``429`` rate limits put a key into cooldown (not permanent failure) and rotate.
    * ``401/402/403`` (invalid or out of credit) mark a key exhausted and rotate.
    * Round-robin pointer + least-recently-used ordering spread load across keys.
    * Cooldown/exhaustion state persists to a JSON file so it survives restarts.
    * Unattended mode only selects loopback inference endpoints. Hosted APIs are
      blocked even when their metadata claims ``free=True`` because free tiers are
      quota-limited and do not guarantee unlimited zero-cost use.
    * When every eligible key is unavailable the pool reports ``free_fallback``.
    * Quota monitoring: when usage reaches the warning threshold (default 95%),
      the key is marked for automatic rotation to the next healthy candidate.

    Secret values never enter pool state or status output.
    """

    COOLDOWN_429_SECONDS = 30.0
    COOLDOWN_ERROR_SECONDS = 15.0
    EXHAUSTION_RECHECK_SECONDS = 300.0
    PROBE_TIMEOUT_SECONDS = 5.0
    QUOTA_WARNING_THRESHOLD_PCT = 95.0

    def __init__(
        self,
        specs: list[LlmKeySpec],
        *,
        prober: KeyProber | None = None,
        state_path: str | None = None,
        clock: Callable[[], float] = monotonic,
        cooldown_429: float = COOLDOWN_429_SECONDS,
        cooldown_error: float = COOLDOWN_ERROR_SECONDS,
        exhaustion_recheck: float = EXHAUSTION_RECHECK_SECONDS,
        quota_warning_threshold_pct: float = QUOTA_WARNING_THRESHOLD_PCT,
    ) -> None:
        self.specs = tuple(specs)
        ids = [spec.id for spec in self.specs]
        if len(ids) != len(set(ids)):
            raise KeyPoolError("llm key pool ids must be unique")
        if not self.specs:
            raise KeyPoolError("llm key pool requires at least one key spec")
        self._prober = prober or HttpKeyProber()
        self.state_path = state_path
        self._clock = clock
        self._cooldown_429 = cooldown_429
        self._cooldown_error = cooldown_error
        self._exhaustion_recheck = exhaustion_recheck
        self._quota_warning = quota_warning_threshold_pct
        self._failures: dict[str, int] = {}
        self._cooldowns: dict[str, float] = {}
        self._exhausted: dict[str, float] = {}
        self._pointer: int = 0
        self._health: dict[str, bool | None] = {}
        self._quota_remaining: dict[str, int] = {}
        self._quota_total: dict[str, int] = {}
        self.free_fallback: bool = False
        self._load_state()

    @classmethod
    def from_environment(cls) -> LlmKeyPool | None:
        """Build a pool from CKNEXUS_LLM_KEYS env var or auto-discovered free providers."""
        raw_keys = os.getenv("CKNEXUS_LLM_KEYS", "").strip()
        if raw_keys:
            try:
                data = json.loads(raw_keys)
                specs = [LlmKeySpec.from_mapping(entry) for entry in data]
            except (json.JSONDecodeError, KeyError) as exc:
                raise KeyPoolError(f"CKNEXUS_LLM_KEYS config error: {exc}") from exc
        else:
            specs = [
                LlmKeySpec(
                    id=provider.id,
                    env_var=provider.env_var,
                    base_url=provider.base_url,
                    model=provider.model,
                    free=provider.free,
                )
                for provider in AUTO_DISCOVER_PROVIDERS
                if provider.id != "qwen" and os.getenv(provider.env_var, "").strip()
            ]

            # Model Studio keys are region-bound. Prefer this workspace's
            # Singapore endpoint and never silently route its key to the global endpoint.
            model_studio_base_url = os.getenv(
                "MODEL_STUDIO_BASE_URL",
                os.getenv(
                    "DASHSCOPE_BASE_URL",
                    "https://ws-6qwky1k48cpsbpbq.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
                ),
            ).strip().rstrip("/")
            model_studio_model = os.getenv(
                "MODEL_STUDIO_MODEL", os.getenv("QWEN_MODEL", "qwen3.6-plus")
            ).strip()
            from urllib.parse import urlparse

            parsed_url = urlparse(model_studio_base_url)
            host = (parsed_url.hostname or "").lower()
            allowed_host = (
                host == "dashscope-intl.aliyuncs.com"
                or host.endswith(".ap-southeast-1.maas.aliyuncs.com")
            )
            if (
                parsed_url.scheme != "https"
                or not allowed_host
                or parsed_url.path != "/compatible-mode/v1"
                or parsed_url.query
                or parsed_url.fragment
            ):
                raise KeyPoolError(
                    "MODEL_STUDIO_BASE_URL must be an HTTPS Singapore Model Studio "
                    "endpoint ending in /compatible-mode/v1"
                )
            if not model_studio_model:
                raise KeyPoolError("MODEL_STUDIO_MODEL must not be empty")

            model_studio_envs = [
                *(f"MODEL_STUDIO_API_KEY_{index}" for index in range(1, 10)),
                "MODEL_STUDIO_API_KEY",
                "DASHSCOPE_API_KEY",
            ]
            model_studio_key_index = 0
            for env_var in model_studio_envs:
                if not os.getenv(env_var, "").strip():
                    continue
                model_studio_key_index += 1
                specs.append(
                    LlmKeySpec(
                        id=f"model-studio-{model_studio_key_index}",
                        env_var=env_var,
                        base_url=model_studio_base_url,
                        model=model_studio_model,
                        free=False,
                    )
                )

        if not specs:
            return None

        return cls(specs)

    def acquire(self) -> LlmKeySelection | None:
        """Acquire the best available key, rotating past exhausted/cooldown'd keys."""
        now = self._clock()
        self._rotate_pointer(len(self.specs))

        for _ in range(len(self.specs)):
            spec = self.specs[self._pointer]
            api_key = os.getenv(spec.env_var, "").strip()

            # Free-tier labels cannot prove unlimited usage or zero billing. In
            # unattended mode only accept loopback endpoints; all hosted routes
            # are blocked regardless of custom CKNEXUS_LLM_KEYS metadata.
            if not self._is_local_endpoint(spec.base_url):
                self._advance_pointer()
                continue

            if not api_key:
                self._advance_pointer()
                continue

            if self._is_exhausted(spec.id, now):
                self._advance_pointer()
                continue

            if self._is_in_cooldown(spec.id, now):
                self._advance_pointer()
                continue

            healthy = self._health.get(spec.id)
            if healthy is False:
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
                free=spec.free,
            )
            self._save_state()
            return selection

        self.free_fallback = True
        return None

    @staticmethod
    def _is_local_endpoint(base_url: str) -> bool:
        """Return true only for loopback endpoints suitable for local inference."""
        try:
            parsed = urlparse(base_url)
            return parsed.scheme in {"http", "https"} and parsed.hostname in {
                "localhost", "127.0.0.1", "::1"
            }
        except (TypeError, ValueError):
            return False

    def report_success(self, key_id: str) -> None:
        self._failures.pop(key_id, None)
        self._cooldowns.pop(key_id, None)
        self._health[key_id] = True
        self._save_state()

    def report_failure(self, key_id: str, *, status_code: int | None = None) -> None:
        self._failures[key_id] = self._failures.get(key_id, 0) + 1

        if status_code == 429:
            self._cooldowns[key_id] = self._clock() + self._cooldown_429
        elif status_code in (401, 402, 403):
            self._exhausted[key_id] = self._clock() + self._exhaustion_recheck
        else:
            self._cooldowns[key_id] = self._clock() + self._cooldown_error

        self._health[key_id] = False
        self._save_state()

    def report_quota_usage(
        self, key_id: str, used: int, total: int, *, threshold_pct: float | None = None
    ) -> None:
        """Report quota usage; auto-mark exhausted if >= threshold."""
        self._quota_remaining[key_id] = max(0, total - used)
        self._quota_total[key_id] = total
        threshold = threshold_pct if threshold_pct is not None else self._quota_warning
        if total > 0:
            pct_used = (used / total) * 100
            if pct_used >= threshold:
                self._exhausted[key_id] = self._clock() + self._exhaustion_recheck
                self._health[key_id] = False

    def probe_all(self) -> None:
        """Probe all configured keys and update health/cooldown/exhaustion state."""
        for spec in self.specs:
            api_key = os.getenv(spec.env_var, "").strip()
            if not api_key:
                self._health[spec.id] = False
                continue

            now = self._clock()
            if self._is_exhausted(spec.id, now):
                continue
            if self._is_in_cooldown(spec.id, now):
                continue

            result = self._prober.probe(spec, api_key, timeout=self.PROBE_TIMEOUT_SECONDS)
            if result.ok:
                self._health[spec.id] = True
                self._failures.pop(spec.id, None)
                self._cooldowns.pop(spec.id, None)
            elif result.status in (401, 403):
                self._mark_exhausted(spec.id, now + self._exhaustion_recheck)
                self._health[spec.id] = False
            elif result.status == 429:
                self._cooldowns[spec.id] = now + self._cooldown_429
                self._health[spec.id] = None
            else:
                self._cooldowns[spec.id] = now + self._cooldown_error
                self._health[spec.id] = None

        self._save_state()

    def status(self) -> tuple[LlmKeyStatus, ...]:
        now = self._clock()
        result: list[LlmKeyStatus] = []
        for spec in self.specs:
            exhausted_until = self._exhausted.get(spec.id, 0)
            cooldown_until = self._cooldowns.get(spec.id, 0)
            in_cooldown = cooldown_until > now
            is_exhausted = exhausted_until > now

            quota_pct = None
            remaining = self._quota_remaining.get(spec.id)
            total = self._quota_total.get(spec.id)
            if remaining is not None and total is not None and total > 0:
                quota_pct = ((total - remaining) / total) * 100

            result.append(
                LlmKeyStatus(
                    key_id=spec.id,
                    provider=spec.id,
                    model=spec.model,
                    free=spec.free,
                    healthy=not in_cooldown
                    and not is_exhausted
                    and self._health.get(spec.id, False),
                    cooldown_until=cooldown_until if in_cooldown else 0.0,
                    consecutive_failures=self._failures.get(spec.id, 0),
                    exhausted=is_exhausted,
                    source="environment" if os.getenv(spec.env_var, "").strip() else "missing_env",
                    quota_percentage_used=quota_pct,
                )
            )
        return tuple(result)

    def _rotate_pointer(self, count: int) -> None:
        self._pointer = self._pointer % max(count, 1)

    def _advance_pointer(self) -> None:
        self._pointer = (self._pointer + 1) % len(self.specs)

    def _is_exhausted(self, key_id: str, now: float) -> bool:
        until = self._exhausted.get(key_id, 0)
        return until > now

    def _is_in_cooldown(self, key_id: str, now: float) -> bool:
        until = self._cooldowns.get(key_id, 0)
        return until > now

    def _is_quota_exhausted(self, key_id: str) -> bool:
        remaining = self._quota_remaining.get(key_id)
        total = self._quota_total.get(key_id)
        if remaining is None or total is None or total <= 0:
            return False
        pct_used = ((total - remaining) / total) * 100
        return pct_used >= self._quota_warning

    def _mark_exhausted(self, key_id: str, until: float) -> None:
        self._exhausted[key_id] = until

    def _load_state(self) -> None:
        if not self.state_path:
            return
        path = os.path.expanduser(self.state_path)
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            self._failures = {k: int(v) for k, v in data.get("failures", {}).items()}
            self._cooldowns = {k: float(v) for k, v in data.get("cooldowns", {}).items()}
            self._exhausted = {k: float(v) for k, v in data.get("exhausted", {}).items()}
            self._health = {k: bool(v) for k, v in data.get("health", {}).items()}
            self._quota_remaining = {k: int(v) for k, v in data.get("quota_remaining", {}).items()}
            self._quota_total = {k: int(v) for k, v in data.get("quota_total", {}).items()}
            self._pointer = int(data.get("pointer", 0))
            self.free_fallback = bool(data.get("free_fallback", False))
        except (json.JSONDecodeError, ValueError, TypeError):
            # Corrupted state file — start fresh
            pass

    def _save_state(self) -> None:
        if not self.state_path:
            return
        path = os.path.expanduser(self.state_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "failures": self._failures,
            "cooldowns": self._cooldowns,
            "exhausted": self._exhausted,
            "health": self._health,
            "quota_remaining": self._quota_remaining,
            "quota_total": self._quota_total,
            "pointer": self._pointer,
            "free_fallback": self.free_fallback,
        }
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)

    def get_status_summary(self) -> dict:
        """Return a machine-readable summary of pool state."""
        statuses = self.status()
        return {
            "total_keys": len(statuses),
            "healthy_keys": sum(1 for s in statuses if s.healthy),
            "exhausted_keys": sum(1 for s in statuses if s.exhausted),
            "free_fallback": self.free_fallback,
            "keys": [
                {
                    "id": s.key_id,
                    "provider": s.provider,
                    "model": s.model,
                    "free": s.free,
                    "healthy": s.healthy,
                    "cooldown_until": s.cooldown_until,
                    "consecutive_failures": s.consecutive_failures,
                    "exhausted": s.exhausted,
                    "quota_percentage_used": s.quota_percentage_used,
                    "source": s.source,
                }
                for s in statuses
            ],
        }
