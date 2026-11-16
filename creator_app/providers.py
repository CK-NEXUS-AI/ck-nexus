from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from creator_app.config import Settings
from creator_app.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)
from creator_app.free_providers import GeminiAdapter, OpenAICompatibleAdapter
from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
    ProviderRouter,
    ProviderRouterPolicy,
)


class UnsafeLocalProviderUrl(ValueError):
    """Raised when a local provider URL could send data outside the loopback host."""


def validate_loopback_base_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeLocalProviderUrl("Local provider URL must use HTTP or HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeLocalProviderUrl("Local provider URL must not contain user information.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise UnsafeLocalProviderUrl(
            "Local provider URL must resolve to an explicit loopback host."
        )
    if parsed.query or parsed.fragment:
        raise UnsafeLocalProviderUrl(
            "Local provider base URL must not contain query or fragment data."
        )
    return url.rstrip("/")


@dataclass(slots=True)
class MockProviderAdapter:
    name: str = "mock"
    kind: ProviderKind = ProviderKind.MOCK
    capabilities: ProviderCapabilities = ProviderCapabilities(
        features=frozenset({"text"}), models=("mock",)
    )

    def is_available(self) -> bool:
        return True

    async def invoke(self, prompt: str) -> str:
        return f"MOCK_PROVIDER\n{prompt[:4000]}"


class OllamaProviderAdapter:
    name = "ollama"
    kind = ProviderKind.LOCAL

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        enabled: bool,
        timeout_seconds: int = 30,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = validate_loopback_base_url(base_url)
        self.model = model.strip()
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urlopen
        self.capabilities = ProviderCapabilities(
            features=frozenset({"text", "local"}),
            models=(self.model,) if self.model else (),
        )

    def is_available(self) -> bool:
        return self.enabled and bool(self.model)

    async def invoke(self, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("Ollama provider is not configured.")
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        def _call() -> str:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            message = body.get("message") or {}
            content = str(message.get("content") or "").strip()
            if not content:
                raise RuntimeError("Ollama response did not contain text output.")
            return content

        return await asyncio.to_thread(_call)


class OpenAIProviderAdapter:
    name = "openai"
    kind = ProviderKind.CLOUD

    def __init__(
        self,
        broker: CredentialBroker,
        *,
        model: str,
        timeout_seconds: int = 90,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.broker = broker
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self._client_factory = client_factory
        self.capabilities = ProviderCapabilities(
            features=frozenset({"text", "agents-sdk", "web-search"}),
            models=(self.model,) if self.model else (),
        )

    def is_available(self) -> bool:
        free_only = os.getenv("CKNEXUS_FREE_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
        return (
            not free_only
            and bool(self.model)
            and self.broker.is_configured(CredentialId.OPENAI_API_KEY, consumer="provider.openai")
        )

    async def invoke(self, prompt: str) -> str:
        try:
            lease = self.broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")
        except CredentialUnavailable as exc:
            raise RuntimeError("OpenAI credential is not configured.") from exc
        api_key = lease.reveal(consumer="provider.openai")
        if self._client_factory is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, timeout=self.timeout_seconds)
        else:
            client = self._client_factory(api_key=api_key, timeout=self.timeout_seconds)
        response = await client.responses.create(model=self.model, input=prompt)
        output = str(getattr(response, "output_text", "") or "").strip()
        if not output:
            raise RuntimeError("OpenAI response did not contain text output.")
        return output


def build_provider_router(settings: Settings, broker: CredentialBroker) -> ProviderRouter:
    providers = []
    if settings.mock_ai:
        providers.append(MockProviderAdapter())
    if settings.ollama_enabled:
        providers.append(
            OllamaProviderAdapter(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                enabled=True,
                timeout_seconds=settings.provider_timeout_seconds,
            )
        )

    # Free cloud providers are explicitly opt-in. Prefer the live-verified
    # OpenRouter zero-price router, then use Gemini as a secondary free-tier path.
    if (
        os.getenv("CKNEXUS_ENABLE_OPENROUTER_FREE", "").strip().lower()
        in {"1", "true", "yes", "on"}
        and os.getenv("OPENROUTER_API_KEY", "").strip()
    ):
        providers.append(
            OpenAICompatibleAdapter(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                env_key="OPENROUTER_API_KEY",
                model=os.getenv("CKNEXUS_OPENROUTER_MODEL", "openrouter/free").strip()
                or "openrouter/free",
                models=("openrouter/free",),
                features=frozenset({"text", "free-model-routing"}),
                timeout_seconds=settings.provider_timeout_seconds,
                extra_headers={"X-Title": "CK-NEXUS"},
            )
        )
    if os.getenv("GEMINI_API_KEY", "").strip():
        providers.append(
            GeminiAdapter(
                model=(
                    os.getenv("CKNEXUS_GEMINI_MODEL", "gemini-3.8-flash").strip()
                    or "gemini-3.8-flash"
                ),
                timeout_seconds=settings.provider_timeout_seconds,
            )
        )

    # In free-only mode, paid OpenAI must not be considered as a fallback even
    # when its credential is present in the legacy environment file.
    free_only = os.getenv("CKNEXUS_FREE_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
    if not free_only:
        providers.append(
            OpenAIProviderAdapter(
                broker,
                model=settings.openai_model,
                timeout_seconds=settings.provider_timeout_seconds,
            )
        )

    return ProviderRouter(
        providers,
        policy=ProviderRouterPolicy(
            local_first=settings.provider_local_first,
            allow_cloud=settings.provider_allow_cloud,
            max_attempts=settings.provider_max_attempts,
            failure_threshold=settings.provider_failure_threshold,
            circuit_cooldown_seconds=settings.provider_circuit_cooldown_seconds,
        ),
    )
