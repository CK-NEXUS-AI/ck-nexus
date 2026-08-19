"""Enhanced provider router — integrates free-tier adapters with circuit breaker.

Extends the original build_provider_router to include all free providers
from provider_hub + provider_registry, with automatic fallback.
"""

from __future__ import annotations

from creator_app.config import Settings
from creator_app.credential_broker import CredentialBroker
from creator_app.free_providers import QuotaTracker, build_free_adapters
from creator_app.provider_router import ProviderRouter, ProviderRouterPolicy
from creator_app.providers import build_provider_router


def build_full_provider_router(
    settings: Settings,
    broker: CredentialBroker,
    *,
    include_free: bool = True,
    quota_tracker: QuotaTracker | None = None,
) -> ProviderRouter:
    """Build a router with all available providers: local, cloud, and free-tier.

    Priority order (local_first=True):
      1. Mock (if mock_ai enabled)
      2. Ollama (if ollama_enabled)
      3. Free-tier cloud adapters (Groq, Cerebras, DeepSeek, Gemini, etc.)
      4. OpenAI (primary cloud)

    The router's circuit breaker handles failures and automatically skips
    degraded providers within the attempt limit.
    """
    base_router = build_provider_router(settings, broker)
    providers = list(base_router._providers)

    if include_free:
        qt = quota_tracker or QuotaTracker()
        free_adapters = build_free_adapters(quota_tracker=qt)

        # Insert free providers BEFORE OpenAI but AFTER local providers
        insert_at = len(providers)
        for i, p in enumerate(providers):
            if p.name == "openai":
                insert_at = i
                break

        for adapter in reversed(free_adapters):
            providers.insert(insert_at, adapter)

    max_attempts = settings.provider_max_attempts
    if include_free:
        max_attempts += len(free_adapters)

    return ProviderRouter(
        providers,
        policy=ProviderRouterPolicy(
            local_first=settings.provider_local_first,
            allow_cloud=settings.provider_allow_cloud,
            max_attempts=max_attempts,
            failure_threshold=settings.provider_failure_threshold,
            circuit_cooldown_seconds=settings.provider_circuit_cooldown_seconds,
        ),
    )
