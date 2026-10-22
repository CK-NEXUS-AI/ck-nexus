"""Fast, fail-closed AI reply plugin for CK-NEXUS.

The plugin routes through the existing environment-backed LLM key pool.
Only approved HTTPS provider hosts are allowed, and secrets never appear in
return values or exception messages.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from creator_app.credentials.llm_keypool import LlmKeyPool, LlmKeySpec


class AutoReplyError(RuntimeError):
    """Safe error with a stable code; never includes credentials or HTTP bodies."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class AutoReplyResult:
    ok: bool
    provider: str
    model: str
    response: str
    latency_ms: int
    attempts: int
    fallback_used: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "model": self.model,
            "response": self.response,
            "latency_ms": self.latency_ms,
            "attempts": self.attempts,
            "fallback_used": self.fallback_used,
        }


_APPROVED_EXACT_HOSTS = frozenset(
    {
        "api.openai.com",
        "api.groq.com",
        "api.mistral.ai",
        "api.cerebras.ai",
        "api.sambanova.ai",
        "openrouter.ai",
        "api.deepseek.com",
        "api.together.xyz",
        "open.bigmodel.cn",
        "api.moonshot.cn",
        "api.x.ai",
        "generativelanguage.googleapis.com",
        "dashscope-intl.aliyuncs.com",
        "dashscope.aliyuncs.com",
    }
)
_APPROVED_HOST_SUFFIXES = (".ap-southeast-1.maas.aliyuncs.com",)
_SYSTEM_PROMPT = (
    "You are CK-NEXUS Fast Reply, a concise AI assistant. Answer the user's "
    "request directly. Never claim to have executed tools, changed files, "
    "connected accounts, or verified results unless the current tool output "
    "proves it. If uncertain, state the limitation clearly."
)


def _approved_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and parsed.query == ""
        and parsed.fragment == ""
        and (
            host in _APPROVED_EXACT_HOSTS
            or any(host.endswith(suffix) for suffix in _APPROVED_HOST_SUFFIXES)
        )
    )


def _environment_pool() -> LlmKeyPool | None:
    """Build a pool while preserving Model Studio's workspace-specific endpoint."""
    pool = LlmKeyPool.from_environment()
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        return pool

    specs = list(pool.specs) if pool is not None else []
    # Older deployed key pools may only know the global DashScope endpoint.
    # Replace that default rather than accidentally sending a regional key globally.
    specs = [spec for spec in specs if spec.env_var != "DASHSCOPE_API_KEY" and spec.id != "qwen"]
    base_url = (
        os.getenv(
            "DASHSCOPE_BASE_URL",
            os.getenv(
                "MODEL_STUDIO_BASE_URL",
                "https://ws-6qwky1k48cpsbpbq.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            ),
        )
        .strip()
        .rstrip("/")
    )
    model = os.getenv("QWEN_MODEL", os.getenv("MODEL_STUDIO_MODEL", "qwen3.6-plus")).strip()
    parsed = urlparse(base_url)
    if not _approved_base_url(base_url) or parsed.path != "/compatible-mode/v1" or not model:
        raise AutoReplyError(
            "INVALID_PROVIDER_CONFIGURATION",
            "Model Studio requires an approved regional HTTPS endpoint and model.",
        )
    specs.append(
        LlmKeySpec(
            id="model-studio-auto",
            env_var="DASHSCOPE_API_KEY",
            base_url=base_url,
            model=model,
            free=False,
        )
    )
    return LlmKeyPool(specs) if specs else None


def _extract_content(payload: object) -> str:
    if not isinstance(payload, dict):
        raise AutoReplyError("INVALID_PROVIDER_RESPONSE", "Provider returned an invalid response.")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise AutoReplyError("INVALID_PROVIDER_RESPONSE", "Provider returned no answer.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise AutoReplyError("INVALID_PROVIDER_RESPONSE", "Provider returned no answer.")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        combined = "\n".join(part for part in parts if part.strip()).strip()
        if combined:
            return combined
    raise AutoReplyError("EMPTY_PROVIDER_RESPONSE", "Provider returned an empty answer.")


class AutoReplyPlugin:
    """Fast provider router with bounded retry/fallback and safe status output."""

    def __init__(
        self,
        *,
        pool_factory: Callable[[], LlmKeyPool | None] | None = None,
        open_url: Callable[..., object] | None = None,
        timeout_seconds: float = 8.0,
        max_attempts: int = 3,
        max_prompt_chars: int = 12_000,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        self._pool_factory = pool_factory or _environment_pool
        self._open_url = open_url or urllib.request.urlopen
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_prompt_chars = max_prompt_chars

    def reply(self, prompt: str, *, max_tokens: int = 512) -> dict[str, object]:
        prompt = prompt.strip()
        if not prompt:
            raise AutoReplyError("EMPTY_PROMPT", "Request must not be empty.")
        if len(prompt) > self.max_prompt_chars:
            raise AutoReplyError("PROMPT_TOO_LONG", "Request exceeds the configured size limit.")
        if not 1 <= max_tokens <= 2048:
            raise AutoReplyError("INVALID_TOKEN_LIMIT", "max_tokens must be between 1 and 2048.")

        pool = self._pool_factory()
        if pool is None:
            raise AutoReplyError(
                "NO_PROVIDER_CONFIGURED", "No AI provider credentials are configured."
            )

        attempted: set[str] = set()
        safe_failure = "AI providers are unavailable or failed within the retry limit."
        started = time.monotonic()

        for attempt in range(1, self.max_attempts + 1):
            selection = pool.acquire()
            if selection is None:
                break
            if selection.key_id in attempted:
                break
            attempted.add(selection.key_id)
            if not _approved_base_url(selection.base_url):
                pool.report_failure(selection.key_id, status_code=403)
                safe_failure = "Configured provider endpoint is not approved."
                continue

            request_body = json.dumps(
                {
                    "model": selection.model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{selection.base_url.rstrip('/')}/chat/completions",
                data=request_body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {selection.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            status_code: int | None = None
            try:
                with self._open_url(request, timeout=self.timeout_seconds) as response:
                    status_code = int(getattr(response, "status", 200))
                    payload = json.loads(response.read())
                answer = _extract_content(payload)
            except urllib.error.HTTPError as exc:
                status_code = exc.code
                pool.report_failure(selection.key_id, status_code=status_code)
                safe_failure = f"Provider request failed with HTTP {status_code}."
                continue
            except AutoReplyError as exc:
                pool.report_failure(selection.key_id, status_code=status_code)
                safe_failure = str(exc)
                continue
            except Exception as exc:
                pool.report_failure(selection.key_id, status_code=status_code)
                safe_failure = f"Provider request failed ({type(exc).__name__})."
                continue

            pool.report_success(selection.key_id)
            return AutoReplyResult(
                ok=True,
                provider=selection.provider,
                model=selection.model,
                response=answer,
                latency_ms=round((time.monotonic() - started) * 1000),
                attempts=attempt,
                fallback_used=attempt > 1,
            ).as_dict()

        raise AutoReplyError("PROVIDERS_UNAVAILABLE", safe_failure)

    def status(self) -> dict[str, object]:
        pool = self._pool_factory()
        if pool is None:
            return {"configured": False, "providers": [], "secret_values_exposed": False}
        summary = pool.get_status_summary()
        return {
            "configured": True,
            "providers": [
                {
                    "id": item["id"],
                    "provider": item["provider"],
                    "model": item["model"],
                    "healthy": (
                        True
                        if item["healthy"]
                        else False
                        if item["consecutive_failures"] > 0 or item["exhausted"]
                        else None
                    ),
                    "health_status": (
                        "healthy"
                        if item["healthy"]
                        else "degraded"
                        if item["consecutive_failures"] > 0 or item["exhausted"]
                        else "unknown"
                    ),
                    "exhausted": item["exhausted"],
                    "consecutive_failures": item["consecutive_failures"],
                    "source": item["source"],
                }
                for item in summary["keys"]
            ],
            "secret_values_exposed": False,
        }
