from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterable

from creator_app.provider_router import ProviderAdapter, ProviderKind


class ProviderLifecycle(StrEnum):
    DISCOVERED = "discovered"
    CONFIG_REQUIRED = "config_required"
    AUTHORIZED = "authorized"
    VERIFIED = "verified"
    ENABLED = "enabled"
    QUARANTINED = "quarantined"


class AuthMechanism(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    BROKERED = "brokered"


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    kind: ProviderKind
    auth: AuthMechanism
    capabilities: frozenset[str]
    credential_id: str | None = None
    official_host: str | None = None
    state: ProviderLifecycle = ProviderLifecycle.DISCOVERED
    evidence_refs: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id is required")
        if self.auth is not AuthMechanism.NONE and not self.credential_id:
            raise ValueError("authenticated providers require a broker credential id")

    @property
    def council_eligible(self) -> bool:
        return self.state in {ProviderLifecycle.VERIFIED, ProviderLifecycle.ENABLED}


class ProviderOnboardingRegistry:
    """Fail-closed provider lifecycle registry.

    Discovery never implies authorization. Authorization never implies verification.
    This registry stores metadata/evidence references only; never raw credentials.
    """

    def __init__(self, descriptors: Iterable[ProviderDescriptor] = ()) -> None:
        self._items: dict[str, ProviderDescriptor] = {}
        for item in descriptors:
            self.register(item)

    def register(self, descriptor: ProviderDescriptor) -> ProviderDescriptor:
        key = descriptor.provider_id.strip().lower()
        if key in self._items:
            raise ValueError(f"provider already registered: {key}")
        self._items[key] = replace(descriptor, provider_id=key)
        return self._items[key]

    def get(self, provider_id: str) -> ProviderDescriptor:
        key = provider_id.strip().lower()
        if key not in self._items:
            raise KeyError(f"unknown provider: {key}")
        return self._items[key]

    def all(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(self._items.values())

    def mark_config_required(
        self, provider_id: str, *, reason: str
    ) -> ProviderDescriptor:
        return self._transition(
            provider_id, ProviderLifecycle.CONFIG_REQUIRED, reason=reason
        )

    def authorize(self, provider_id: str, *, evidence_ref: str) -> ProviderDescriptor:
        current = self.get(provider_id)
        if current.state not in {
            ProviderLifecycle.DISCOVERED,
            ProviderLifecycle.CONFIG_REQUIRED,
        }:
            raise RuntimeError("provider authorization transition is not allowed")
        return self._transition(
            provider_id, ProviderLifecycle.AUTHORIZED, evidence_ref=evidence_ref
        )

    def verify(self, provider_id: str, *, evidence_ref: str) -> ProviderDescriptor:
        current = self.get(provider_id)
        if current.state is not ProviderLifecycle.AUTHORIZED:
            raise RuntimeError("provider must be authorized before verification")
        return self._transition(
            provider_id, ProviderLifecycle.VERIFIED, evidence_ref=evidence_ref
        )

    def enable(self, provider_id: str, *, evidence_ref: str) -> ProviderDescriptor:
        current = self.get(provider_id)
        if current.state is not ProviderLifecycle.VERIFIED:
            raise RuntimeError("provider must be verified before enablement")
        return self._transition(
            provider_id, ProviderLifecycle.ENABLED, evidence_ref=evidence_ref
        )

    def quarantine(
        self, provider_id: str, *, reason: str, evidence_ref: str | None = None
    ) -> ProviderDescriptor:
        return self._transition(
            provider_id,
            ProviderLifecycle.QUARANTINED,
            reason=reason,
            evidence_ref=evidence_ref,
        )

    def eligible_ids(
        self, *, required_capabilities: Iterable[str] = ()
    ) -> tuple[str, ...]:
        required = frozenset(required_capabilities)
        return tuple(
            item.provider_id
            for item in self._items.values()
            if item.council_eligible and required.issubset(item.capabilities)
        )

    def bind_adapter(
        self, provider_id: str, adapter: ProviderAdapter
    ) -> ProviderAdapter:
        descriptor = self.get(provider_id)
        if not descriptor.council_eligible:
            raise PermissionError("provider is not verified/enabled")
        if adapter.name != descriptor.provider_id:
            raise ValueError("adapter name does not match provider descriptor")
        if adapter.kind is not descriptor.kind:
            raise ValueError("adapter kind does not match provider descriptor")
        if not descriptor.capabilities.issubset(adapter.capabilities.features):
            raise ValueError("adapter capabilities do not satisfy provider descriptor")
        binding_id = getattr(adapter, "credential_binding_id", None)
        if binding_id is not None and binding_id != descriptor.credential_id:
            raise ValueError(
                "adapter credential binding does not match provider descriptor"
            )
        official_host = getattr(adapter, "official_host", None)
        if official_host is not None and official_host != descriptor.official_host:
            raise ValueError("adapter host does not match provider descriptor")
        if not adapter.is_available():
            raise RuntimeError("provider adapter is not currently available")
        return adapter

    def _transition(
        self,
        provider_id: str,
        state: ProviderLifecycle,
        *,
        reason: str | None = None,
        evidence_ref: str | None = None,
    ) -> ProviderDescriptor:
        current = self.get(provider_id)
        refs = current.evidence_refs + ((evidence_ref,) if evidence_ref else ())
        updated = replace(current, state=state, evidence_refs=refs, reason=reason)
        self._items[current.provider_id] = updated
        return updated


def default_provider_catalog() -> tuple[ProviderDescriptor, ...]:
    cloud = ProviderKind.CLOUD
    return (
        ProviderDescriptor(
            "openai",
            "OpenAI",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "openai.api_key",
            "api.openai.com",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
        ProviderDescriptor(
            "gemini",
            "Google Gemini",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "google.gemini.api_key",
            "generativelanguage.googleapis.com",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
        ProviderDescriptor(
            "anthropic",
            "Anthropic Claude",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "anthropic.api_key",
            "api.anthropic.com",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
        ProviderDescriptor(
            "groq",
            "Groq",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "groq.api_key",
            "api.groq.com",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
        ProviderDescriptor(
            "deepseek",
            "DeepSeek",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "deepseek.api_key",
            "api.deepseek.com",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
        ProviderDescriptor(
            "openrouter",
            "OpenRouter",
            cloud,
            AuthMechanism.BROKERED,
            frozenset({"text"}),
            "openrouter.api_key",
            "openrouter.ai",
            ProviderLifecycle.CONFIG_REQUIRED,
        ),
    )
