from __future__ import annotations

import asyncio
import json
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
from creator_app.real_provider_adapters import build_real_provider_adapter
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
        return bool(self.model) and self.broker.is_configured(
            CredentialId.OPENAI_API_KEY, consumer="provider.openai"
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
    providers.append(
        OpenAIProviderAdapter(
            broker,
            model=settings.openai_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
    )
    for provider_id, model in (
        ("gemini", settings.gemini_model),
        ("anthropic", settings.anthropic_model),
        ("groq", settings.groq_model),
        ("deepseek", settings.deepseek_model),
        ("openrouter", settings.openrouter_model),
    ):
        if model:
            providers.append(
                build_real_provider_adapter(
                    provider_id,
                    broker,
                    model=model,
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
