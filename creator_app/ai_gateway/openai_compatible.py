"""Governed OpenAI-compatible provider adapter primitives.

This module intentionally does not read environment variables, API keys, or secret stores.
Credential material stays behind a caller-supplied transport/credential broker boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from .contracts import ModelDescriptor, ProviderSnapshot


@dataclass(frozen=True, slots=True)
class OpenAICompatibleEndpoint:
    """Non-secret endpoint identity for an OpenAI-compatible provider."""

    provider_id: str
    base_url: str
    credential_ref: str
    runtime_id: str = "openai-compatible"
    allow_local_http: bool = False

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip()
        credential_ref = self.credential_ref.strip()
        runtime_id = self.runtime_id.strip()
        if not provider_id or not credential_ref or not runtime_id:
            raise ValueError("provider_id, credential_ref and runtime_id must not be empty")
        if not credential_ref.startswith("broker://"):
            raise ValueError("credential_ref must be a broker:// reference, never raw secret material")

        parsed = urlsplit(self.base_url)
        if parsed.username or parsed.password:
            raise ValueError("credentials must not be embedded in base_url")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain query or fragment")
        if not parsed.hostname:
            raise ValueError("base_url must contain a hostname")

        is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme == "https":
            return
        if parsed.scheme == "http" and is_local and self.allow_local_http:
            return
        raise ValueError("remote OpenAI-compatible endpoints require HTTPS")


class OpenAICompatibleProviderAdapter:
    """Provider-neutral adapter backed by an injected brokered transport.

    The transport receives a credential *reference*, never credential material. The
    credential broker/transport is responsible for resolving a scoped secret lease.
    """

    def __init__(
        self,
        *,
        endpoint: OpenAICompatibleEndpoint,
        models: tuple[ModelDescriptor, ...],
        transport: Callable[[OpenAICompatibleEndpoint, str, str], str],
        healthy: Callable[[], bool] | None = None,
    ) -> None:
        if any(model.provider_id != endpoint.provider_id for model in models):
            raise ValueError("all models must belong to endpoint.provider_id")
        if any(model.runtime_id != endpoint.runtime_id for model in models):
            raise ValueError("all models must match endpoint.runtime_id")
        self._endpoint = endpoint
        self._models = models
        self._transport = transport
        self._healthy = healthy or (lambda: True)

    @property
    def provider_id(self) -> str:
        return self._endpoint.provider_id

    @property
    def credential_ref(self) -> str:
        """Return only the broker reference; raw secret material is never available here."""
        return self._endpoint.credential_ref

    def discover_models(self) -> ProviderSnapshot:
        return ProviderSnapshot(
            provider_id=self.provider_id,
            healthy=bool(self._healthy()),
            models=self._models,
            source="openai_compatible_static_attested_catalog",
        )

    def invoke(self, model_id: str, prompt: str) -> str:
        model_id = model_id.strip()
        prompt = prompt.strip()
        if not model_id or not prompt:
            raise ValueError("model_id and prompt must not be empty")
        if model_id not in {model.model_id for model in self._models}:
            raise ValueError("model_id is not registered for this provider")
        return self._transport(self._endpoint, model_id, prompt)
