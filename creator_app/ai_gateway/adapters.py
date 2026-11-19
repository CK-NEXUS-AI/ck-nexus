"""Minimal adapter primitives for provider plugins.

The gateway core never fetches secrets and never assumes a provider-specific HTTP API.
Provider plugins own credential leases and transport, while the core sees only model
metadata and normalized text output.
"""

from __future__ import annotations

from collections.abc import Callable

from .contracts import ProviderSnapshot


class CallbackProviderAdapter:
    """Small provider adapter useful for local, MCP, SDK and HTTP-backed plugins."""

    def __init__(
        self,
        *,
        provider_id: str,
        discoverer: Callable[[], ProviderSnapshot],
        invoker: Callable[[str, str], str],
    ) -> None:
        normalized = provider_id.strip()
        if not normalized:
            raise ValueError("provider_id must not be empty")
        self._provider_id = normalized
        self._discoverer = discoverer
        self._invoker = invoker

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def discover_models(self) -> ProviderSnapshot:
        snapshot = self._discoverer()
        if snapshot.provider_id != self._provider_id:
            raise ValueError("provider snapshot identity mismatch")
        return snapshot

    def invoke(self, model_id: str, prompt: str) -> str:
        if not model_id.strip() or not prompt.strip():
            raise ValueError("model_id and prompt must not be empty")
        return self._invoker(model_id, prompt)
