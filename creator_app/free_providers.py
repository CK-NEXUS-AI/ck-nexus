"""Free-tier provider adapters for CK-NEXUS multi-provider routing.

Each adapter conforms to the ProviderAdapter protocol from provider_router.py.
All use OpenAI-compatible chat completions endpoints (most free providers do).
Keys are read from environment variables — never logged or stored in memory.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
)


def _require_safe_provider_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and host:
        return
    if parsed.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}:
        return
    raise ValueError("Provider endpoint must use HTTPS, except loopback HTTP")


# ── Quota Tracker ────────────────────────────────────────────────────────────


@dataclass
class QuotaWindow:
    """Tracks usage within a sliding time window."""

    requests: int = 0
    tokens_used: int = 0
    window_start: float = field(default_factory=time.monotonic)
    last_error: str = ""
    last_error_time: float = 0.0


class QuotaTracker:
    """Per-provider quota tracking with sliding windows.

    Free tiers typically limit:
    - Requests per minute (RPM)
    - Tokens per minute (TPM)
    - Requests per day (RPD)

    This tracker monitors all three and signals when a provider is exhausted.
    """

    def __init__(self, windows_seconds: float = 60.0):
        self._windows_seconds = windows_seconds
        self._data: dict[str, QuotaWindow] = defaultdict(QuotaWindow)

    def record(self, provider: str, tokens: int = 0) -> None:
        window = self._data[provider]
        now = time.monotonic()
        if now - window.window_start > self._windows_seconds:
            window.requests = 0
            window.tokens_used = 0
            window.window_start = now
        window.requests += 1
        window.tokens_used += tokens

    def record_error(self, provider: str, error: str) -> None:
        window = self._data[provider]
        window.last_error = error
        window.last_error_time = time.monotonic()

    def is_rate_limited(self, provider: str) -> bool:
        window = self._data[provider]
        now = time.monotonic()
        return (
            bool(window.last_error)
            and "429" in window.last_error
            and now - window.last_error_time < self._windows_seconds
        )

    def stats(self, provider: str) -> dict[str, Any]:
        window = self._data[provider]
        return {
            "requests": window.requests,
            "tokens": window.tokens_used,
            "window_seconds": self._windows_seconds,
            "rate_limited": self.is_rate_limited(provider),
            "last_error": window.last_error[:100] if window.last_error else None,
        }


# ── Base OpenAI-Compatible Adapter ──────────────────────────────────────────


class OpenAICompatibleAdapter:
    """Base adapter for providers exposing OpenAI-compatible /chat/completions."""

    kind = ProviderKind.CLOUD

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        env_key: str,
        model: str,
        models: tuple[str, ...] = (),
        features: frozenset[str] = frozenset({"text"}),
        timeout_seconds: int = 30,
        extra_headers: dict[str, str] | None = None,
        quota_tracker: QuotaTracker | None = None,
        opener: Any | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.env_key = env_key
        self.model = model
        self._models = models or (model,)
        self.timeout_seconds = timeout_seconds
        self._extra_headers = extra_headers or {}
        self._quota = quota_tracker
        self._opener = opener
        self.capabilities = ProviderCapabilities(
            features=features,
            models=self._models,
        )

    def _get_key(self) -> str:
        return os.environ.get(self.env_key, "").strip()

    def is_available(self) -> bool:
        key = self._get_key()
        if not key:
            return False
        return not (self._quota and self._quota.is_rate_limited(self.name))

    async def invoke(self, prompt: str) -> str:
        key = self._get_key()
        if not key:
            raise RuntimeError(f"{self.name}: API key not set in {self.env_key}")

        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.7,
            }
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            **self._extra_headers,
        }

        endpoint = f"{self.base_url}/chat/completions"
        _require_safe_provider_url(endpoint)
        request = Request(
            endpoint,
            data=payload,
            method="POST",
            headers=headers,
        )

        def _call() -> str:
            try:
                opener = self._opener or urlopen
                with opener(request, timeout=self.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except Exception as exc:
                if self._quota:
                    self._quota.record_error(self.name, str(exc))
                raise

            choices = body.get("choices", [])
            if not choices:
                raise RuntimeError(f"{self.name}: no choices in response")
            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                raise RuntimeError(f"{self.name}: empty response content")

            usage = body.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            if self._quota:
                self._quota.record(self.name, tokens=total_tokens)

            return content

        return await asyncio.to_thread(_call)


# ── Gemini uses a different endpoint format ──────────────────────────────────


class GeminiAdapter:
    """Google Gemini adapter using the generateContent REST API."""

    kind = ProviderKind.CLOUD

    def __init__(
        self,
        *,
        model: str = "gemini-2.0-flash",
        timeout_seconds: int = 30,
        quota_tracker: QuotaTracker | None = None,
    ) -> None:
        self.name = "gemini"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._quota = quota_tracker
        self.capabilities = ProviderCapabilities(
            features=frozenset({"text", "vision"}),
            models=("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"),
        )

    def _get_key(self) -> str:
        return os.environ.get("GEMINI_API_KEY", "").strip()

    def is_available(self) -> bool:
        key = self._get_key()
        if not key:
            return False
        return not (self._quota and self._quota.is_rate_limited(self.name))

    async def invoke(self, prompt: str) -> str:
        key = self._get_key()
        if not key:
            raise RuntimeError("Gemini: GEMINI_API_KEY not set")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent?key={key}"
        )
        _require_safe_provider_url(url)
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.7},
            }
        ).encode("utf-8")

        request = Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
            },
        )

        def _call() -> str:
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                    body = json.loads(response.read().decode("utf-8"))
            except Exception as exc:
                if self._quota:
                    self._quota.record_error(self.name, str(exc))
                raise

            candidates = body.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini: no candidates in response")
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts).strip()
            if not content:
                raise RuntimeError("Gemini: empty response content")

            usage = body.get("usageMetadata", {})
            total_tokens = usage.get("totalTokenCount", 0)
            if self._quota:
                self._quota.record(self.name, tokens=total_tokens)

            return content

        return await asyncio.to_thread(_call)


# ── Concrete Free-Tier Adapters ─────────────────────────────────────────────


def build_free_adapters(
    quota_tracker: QuotaTracker | None = None,
    *,
    allow_limited_free_tier: bool = False,
) -> list[Any]:
    """Build bounded hosted free-tier adapters only after explicit opt-in.

    Free hosted tiers are quota-limited and are not an unlimited inference path.
    Unattended callers therefore receive no hosted adapters by default. The
    opt-in exists for separately approved, quota-bounded development workflows.
    """
    if not allow_limited_free_tier:
        return []
    qt = quota_tracker or QuotaTracker()
    adapters: list[Any] = []

    # Groq — fast Llama/Mixtral
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                env_key="GROQ_API_KEY",
                model="llama-3.3-70b-versatile",
                models=("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"),
                features=frozenset({"text", "fast"}),
                timeout_seconds=15,
                quota_tracker=qt,
            )
        )

    # Cerebras — ultra-fast inference
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="cerebras",
                base_url="https://api.cerebras.ai/v1",
                env_key="CEREBRAS_API_KEY",
                model="llama-3.3-70b",
                models=("llama-3.3-70b", "llama-3.1-8b"),
                features=frozenset({"text", "fast"}),
                timeout_seconds=15,
                quota_tracker=qt,
            )
        )

    # DeepSeek — strong reasoning
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="deepseek",
                base_url="https://api.deepseek.com/v1",
                env_key="DEEPSEEK_API_KEY",
                model="deepseek-chat",
                models=("deepseek-chat", "deepseek-reasoner"),
                features=frozenset({"text", "reasoning"}),
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # OpenRouter — gateway to many free models
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                env_key="OPENROUTER_API_KEY",
                model="meta-llama/llama-3.3-70b-instruct:free",
                models=(
                    "meta-llama/llama-3.3-70b-instruct:free",
                    "qwen/qwen-2.5-72b-instruct:free",
                    "mistralai/mistral-7b-instruct:free",
                ),
                features=frozenset({"text", "many-models"}),
                timeout_seconds=30,
                extra_headers={"HTTP-Referer": "https://ck-nexus.local"},
                quota_tracker=qt,
            )
        )

    # Together AI
    together_key = os.environ.get("TOGETHER_API_KEY", "").strip()
    if together_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="together",
                base_url="https://api.together.xyz/v1",
                env_key="TOGETHER_API_KEY",
                model="meta-llama/Llama-3-70b-chat-hf",
                models=("meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"),
                features=frozenset({"text"}),
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # Mistral AI
    mistral_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="mistral",
                base_url="https://api.mistral.ai/v1",
                env_key="MISTRAL_API_KEY",
                model="mistral-small-latest",
                models=("mistral-small-latest", "mistral-tiny"),
                features=frozenset({"text"}),
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # Google Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        adapters.append(
            GeminiAdapter(
                model="gemini-2.0-flash",
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # SambaNova
    sambanova_key = os.environ.get("SAMBANOVA_API_KEY", "").strip()
    if sambanova_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="sambanova",
                base_url="https://api.sambanova.ai/v1",
                env_key="SAMBANOVA_API_KEY",
                model="Meta-Llama-3.3-70B-Instruct",
                models=("Meta-Llama-3.3-70B-Instruct",),
                features=frozenset({"text"}),
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # Cohere
    cohere_key = os.environ.get("COHERE_API_KEY", "").strip()
    if cohere_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="cohere",
                base_url="https://api.cohere.com/v2",
                env_key="COHERE_API_KEY",
                model="command-r",
                models=("command-r", "command-r-plus"),
                features=frozenset({"text", "rag"}),
                timeout_seconds=30,
                quota_tracker=qt,
            )
        )

    # HuggingFace
    hf_key = os.environ.get("HUGGINGFACE_API_KEY", "").strip()
    if hf_key:
        adapters.append(
            OpenAICompatibleAdapter(
                name="huggingface",
                base_url="https://api-inference.huggingface.co/v1",
                env_key="HUGGINGFACE_API_KEY",
                model="meta-llama/Llama-3.3-70B-Instruct",
                models=("meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"),
                features=frozenset({"text"}),
                timeout_seconds=60,
                quota_tracker=qt,
            )
        )

    return adapters
