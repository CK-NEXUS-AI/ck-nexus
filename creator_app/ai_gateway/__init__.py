"""CK-NEXUS capability-based universal AI gateway."""

from .adapters import CallbackProviderAdapter
from .contracts import (
    AIProvider,
    AttestationState,
    DataClass,
    GatewayRequest,
    GatewayResponse,
    GenerationProfile,
    ModelCapability,
    ModelDescriptor,
    ModelProvenance,
    ModelRiskClass,
    ModelUseLane,
    ProviderSnapshot,
    ReasoningEffort,
)
from .gateway import AIGateway, NoEligibleModel
from .model_attestation import (
    CapabilityAttestation,
    CapabilityCheck,
    attest_capabilities,
    behavioral_fingerprint,
)
from .model_governance import ModelPolicyDecision, authorize_model_use, infer_effective_risk
from .openai_compatible import OpenAICompatibleEndpoint, OpenAICompatibleProviderAdapter

__all__ = [
    "AIGateway",
    "AIProvider",
    "AttestationState",
    "CallbackProviderAdapter",
    "CapabilityAttestation",
    "CapabilityCheck",
    "DataClass",
    "GatewayRequest",
    "GatewayResponse",
    "GenerationProfile",
    "ModelCapability",
    "ModelDescriptor",
    "ModelPolicyDecision",
    "ModelProvenance",
    "ModelRiskClass",
    "ModelUseLane",
    "NoEligibleModel",
    "OpenAICompatibleEndpoint",
    "OpenAICompatibleProviderAdapter",
    "ProviderSnapshot",
    "ReasoningEffort",
    "attest_capabilities",
    "authorize_model_use",
    "behavioral_fingerprint",
    "infer_effective_risk",
]
