from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from creator_app.free_providers import AUTO_DISCOVER_PROVIDERS


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
    * When every key is unavailable the pool reports ``free_fallback`` so callers
      can switch to local/free mode instead of failing hard.

    Secret values never enter pool state or status output.
    """

    COOLDOWN_429_SECONDS = 30.0
    COOLDOWN_ERROR_SECONDS = 15.0
    EXHAUSTION_RECHECK_SECONDS = 300.0
    PROBE_TIMEOUT_SECONDS = 5.0

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
        self._cooldowns: dict[str, float] = {}
        self._exhausted_until: dict[str, float] = {}
        self._failures: dict[str, int] = {spec.id: 0 for spec in self.specs}
        self._cursor = 0
        self._load_state()

    @classmethod
    def from_environment(
        cls,
        *,
        state_path: str | None = None,
        explicit_specs: list[LlmKeySpec] | None = None,
    ) -> LlmKeyPool | None:
        """Build a pool from ``CKNEXUS_LLM_KEYS`` JSON or auto-discovered providers.

        Returns None when no LLM key environment is configured, so callers can keep
        the existing single-key credential broker path untouched.
        """
        specs: list[LlmKeySpec] = []
        if explicit_specs:
            specs.extend(explicit_specs)
        raw = os.getenv("CKNEXUS_LLM_KEYS", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise KeyPoolError(f"CKNEXUS_LLM_KEYS is not valid JSON: {exc}") from exc
            if not isinstance(parsed, list):
                raise KeyPoolError("CKNEXUS_LLM_KEYS must be a JSON list of key specs")
            specs.extend(LlmKeySpec.from_mapping(item) for item in parsed)
        for provider in AUTO_DISCOVER_PROVIDERS:
            value = os.getenv(provider.env_var, "").strip()
            if value:
                specs.append(
                    LlmKeySpec(
                        id=provider.id,
                        env_var=provider.env_var,
                        base_url=provider.base_url,
                        model=provider.model,
                        free=provider.free,
                    )
                )
        if not specs:
            return None
        return cls(specs, state_path=state_path)

    # ---------- state persistence ----------

    def _load_state(self) -> None:
        if not self.state_path or not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, ValueError):
            return
        now = self._clock()
        self._cursor = int(raw.get("cursor", 0)) % max(1, len(self.specs))
        for key_id, ts in raw.get("cooldowns", {}).items():
            if float(ts) > now:
                self._cooldowns[key_id] = float(ts)
        for key_id, ts in raw.get("exhausted_until", {}).items():
            if float(ts) > now:
                self._exhausted_until[key_id] = float(ts)

    def save_state(self) -> None:
        if not self.state_path:
            return
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "cursor": self._cursor,
                        "cooldowns": self._cooldowns,
                        "exhausted_until": self._exhausted_until,
                    },
                    handle,
                    sort_keys=True,
                )
        except OSError:
            return  # state persistence is best-effort; never fails a run

    # ---------- health ----------

    def probe_key(self, spec: LlmKeySpec) -> ProbeResult:
        api_key = os.getenv(spec.env_var, "").strip()
        if not api_key:
            return ProbeResult(status=None, ok=False, detail="missing_env")
        return self._prober.probe(spec, api_key, timeout=self.PROBE_TIMEOUT_SECONDS)

    def probe_all(self) -> None:
        now = self._clock()
        for spec in self.specs:
            result = self.probe_key(spec)
            if result.status == 200:
                self._cooldowns.pop(spec.id, None)
                self._exhausted_until.pop(spec.id, None)
                self._failures[spec.id] = 0
            elif result.status in (401, 402, 403):
                self._exhausted_until[spec.id] = now + self._exhaustion_recheck
                self._cooldowns.pop(spec.id, None)
                self._failures[spec.id] = self._failures.get(spec.id, 0) + 1
            else:  # 429, 5xx, network errors
                self._cooldowns[spec.id] = now + self._cooldown_error
        self.save_state()

    # ---------- selection ----------

    def acquire(self) -> LlmKeySelection | None:
        """Return the next available key or None when the whole pool is unavailable."""
        now = self._clock()
        ordered = self._ordered_candidates(now)
        if not ordered:
            return None
        self._cursor = (self._cursor + 1) % max(1, len(self.specs))
        self.save_state()
        spec = ordered[0]
        api_key = os.getenv(spec.env_var, "").strip()
        if not api_key:
            return None
        return LlmKeySelection(
            key_id=spec.id,
            api_key=api_key,
            base_url=spec.base_url,
            model=spec.model,
            provider=spec.id,
            free=spec.free,
        )

    def _ordered_candidates(self, now: float) -> list[LlmKeySpec]:
        candidates = [
            spec
            for spec in self.specs
            if (
                now >= self._cooldowns.get(spec.id, 0.0)
                and now >= self._exhausted_until.get(spec.id, 0.0)
            )
        ]
        if not candidates:
            return []
        cursor = self._cursor % len(candidates)
        rotated = candidates[cursor:] + candidates[:cursor]
        rotated.sort(key=lambda spec: self._failures.get(spec.id, 0))  # least-failed first
        return rotated

    # ---------- feedback ----------

    def report_status(self, key_id: str, http_status: int) -> None:
        now = self._clock()
        if http_status == 429:
            self._cooldowns[key_id] = now + self._cooldown_429
            self._failures[key_id] = self._failures.get(key_id, 0) + 1
        elif http_status in (401, 402, 403):
            self._exhausted_until[key_id] = now + self._exhaustion_recheck
            self._cooldowns.pop(key_id, None)
            self._failures[key_id] = self._failures.get(key_id, 0) + 1
        elif http_status >= 500:
            self._cooldowns[key_id] = now + self._cooldown_error
            self._failures[key_id] = self._failures.get(key_id, 0) + 1
        self.save_state()

    def report_failure(self, key_id: str) -> None:
        self.report_status(key_id, 500)

    def report_success(self, key_id: str) -> None:
        self._failures[key_id] = 0
        self._cooldowns.pop(key_id, None)
        self._exhausted_until.pop(key_id, None)
        self.save_state()

    @property
    def free_fallback(self) -> bool:
        now = self._clock()
        return not any(
            now >= self._cooldowns.get(spec.id, 0.0)
            and now >= self._exhausted_until.get(spec.id, 0.0)
            for spec in self.specs
        )

    def status(self) -> list[LlmKeyStatus]:
        now = self._clock()
        result: list[LlmKeyStatus] = []
        for spec in self.specs:
            cooldown_until = self._cooldowns.get(spec.id, 0.0)
            exhausted_until = self._exhausted_until.get(spec.id, 0.0)
            available = now >= cooldown_until and now >= exhausted_until
            result.append(
                LlmKeyStatus(
                    key_id=spec.id,
                    provider=spec.id,
                    model=spec.model,
                    free=spec.free,
                    healthy=available,
                    cooldown_until=cooldown_until,
                    consecutive_failures=self._failures.get(spec.id, 0),
                    exhausted=now < exhausted_until,
                    source="environment" if os.getenv(spec.env_var, "").strip() else "missing_env",
                )
            )
        return result


@dataclass(frozen=True, slots=True)
class OpenAICredential:
    """Resolved credential for one OpenAI-compatible run (secret-safe)."""

    api_key: str
    base_url: str | None
    model: str | None
    key_id: str | None
    source: str


def acquire_openai_credential(
    broker: object,
    pool: LlmKeyPool | None,
    *,
    consumer: str,
    default_model: str,
) -> OpenAICredential | None:
    """Prefer a healthy pooled key, then fall back to the broker's env credential.

    Returns None when no credential is available so callers can trigger the
    free-mode fallback path instead of failing hard.
    """
    if pool is not None:
        selection = pool.acquire()
        if selection is not None:
            return OpenAICredential(
                api_key=selection.api_key,
                base_url=selection.base_url,
                model=selection.model,
                key_id=selection.key_id,
                source="llm_key_pool",
            )
    try:
        from creator_app.credential_broker import CredentialId, CredentialUnavailable

        lease = broker.acquire(CredentialId.OPENAI_API_KEY, consumer=consumer)
    except (CredentialUnavailable, AttributeError):
        return None
    return OpenAICredential(
        api_key=lease.reveal(consumer=consumer),
        base_url=None,
        model=default_model,
        key_id=None,
        source="credential_broker",
    )
