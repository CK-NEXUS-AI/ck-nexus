"""CK-NEXUS capability-based universal AI gateway."""

from .adapters import CallbackProviderAdapter
from .contracts import (
    AIProvider,
    DataClass,
    GatewayRequest,
    GatewayResponse,
    ModelCapability,
    ModelDescriptor,
    ProviderSnapshot,
)
from .gateway import AIGateway, NoEligibleModel

__all__ = [
    "AIGateway",
    "AIProvider",
    "CallbackProviderAdapter",
    "DataClass",
    "GatewayRequest",
    "GatewayResponse",
    "ModelCapability",
    "ModelDescriptor",
    "NoEligibleModel",
    "ProviderSnapshot",
]
