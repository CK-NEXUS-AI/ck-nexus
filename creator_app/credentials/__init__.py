"""CK-NEXUS Universal Credential Broker + Capability Router package.

This package integrates:
- Credential Broker (least-privilege credential leasing)
- LLM Key Pool (auto-rotation on quota exhaustion)
- Sticky Free Fallback Key Pool (85% remaining guard -> free/local-only)
- Credit Telemetry Fabric (authoritative credit/cost normalization)
- Zero-Cost Local Runtime (verified loopback Ollama, cloud models denied)
- Capability Router (provider selection with circuit breaker)
- Capability Registry (canonical capability matrix)
- Gmail OAuth Connector (OAuth2, no raw token extraction)

Authority chain:
USER -> ACCESS -> GOVERNOR -> POLICY -> CREDENTIAL BROKER
-> CAPABILITY ROUTER -> TOOL/API -> VERIFICATION -> EVIDENCE
"""

from creator_app.credentials.capability_registry import (
    CANONICAL_CAPABILITIES,
    Capability,
    CapabilityRegistry,
    CapabilitySpec,
    ProviderCandidate,
)
from creator_app.credentials.credential_broker import (
    CredentialAccessDenied,
    CredentialBroker,
    CredentialId,
    CredentialStatus,
    CredentialUnavailable,
    PersistentCredentialStore,
    SecretLease,
)
from creator_app.credentials.credit_telemetry import (
    CreditSnapshot,
    CreditTelemetryAdapter,
    CreditTelemetryFabric,
    DeepSeekBalanceAdapter,
    OpenAICostBudgetAdapter,
    OpenRouterCreditsAdapter,
)
from creator_app.credentials.free_fallback_keypool import FreeFallbackKeyPool
from creator_app.credentials.gmail_oauth_connector import (
    GmailConfig,
    GmailConnector,
    GmailConnectorError,
)
from creator_app.credentials.llm_keypool import (
    KeyPoolError,
    LlmKeyPool,
    LlmKeySelection,
    LlmKeySpec,
    LlmKeyStatus,
)
from creator_app.credentials.zero_cost_runtime import (
    LocalOllamaRuntime,
    ZeroCostRuntimeStatus,
    ZeroCostRuntimeUnavailable,
)

__all__ = [
    "CredentialBroker",
    "CredentialId",
    "CredentialAccessDenied",
    "CredentialUnavailable",
    "SecretLease",
    "CredentialStatus",
    "PersistentCredentialStore",
    "LlmKeyPool",
    "FreeFallbackKeyPool",
    "LlmKeySelection",
    "LlmKeySpec",
    "LlmKeyStatus",
    "KeyPoolError",
    "CreditSnapshot",
    "CreditTelemetryAdapter",
    "CreditTelemetryFabric",
    "OpenRouterCreditsAdapter",
    "OpenAICostBudgetAdapter",
    "DeepSeekBalanceAdapter",
    "LocalOllamaRuntime",
    "ZeroCostRuntimeStatus",
    "ZeroCostRuntimeUnavailable",
    "Capability",
    "CapabilityRegistry",
    "CapabilitySpec",
    "ProviderCandidate",
    "CANONICAL_CAPABILITIES",
    "GmailConnector",
    "GmailConnectorError",
    "GmailConfig",
]
