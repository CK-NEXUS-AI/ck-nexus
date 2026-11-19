"""Compatibility facade for the canonical provider router API.

Post-P0 capability routing lives under ``creator_app.credentials`` but existing
CK-NEXUS modules still import ``creator_app.provider_router``. Re-export the
same class objects so enum/type identity remains stable while migration is
reviewed.
"""

from creator_app.credentials.capability_router import (
    ProviderAdapter,
    ProviderCapabilities,
    ProviderInvoke,
    ProviderKind,
    ProviderRouteError,
    ProviderRouter,
    ProviderRouterPolicy,
    ProviderSelection,
    ProviderStatus,
)

__all__ = [
    "ProviderAdapter",
    "ProviderCapabilities",
    "ProviderInvoke",
    "ProviderKind",
    "ProviderRouteError",
    "ProviderRouter",
    "ProviderRouterPolicy",
    "ProviderSelection",
    "ProviderStatus",
]
