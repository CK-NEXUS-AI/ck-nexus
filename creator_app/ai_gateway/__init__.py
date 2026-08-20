"""CK-NEXUS capability-based universal AI gateway."""

from .adapters import CallbackProviderAdapter
from .catalog import (
    GlobalCapabilityCatalog,
    ProviderCapabilityDeclaration,
    ProviderClass,
)
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
from .inventory import CapabilityInventory, ProviderInventoryRecord, ProviderStage

__all__ = [
    "AIGateway",
    "AIProvider",
    "CallbackProviderAdapter",
    "CapabilityInventory",
    "DataClass",
    "GatewayRequest",
    "GatewayResponse",
    "GlobalCapabilityCatalog",
    "ModelCapability",
    "ModelDescriptor",
    "NoEligibleModel",
    "ProviderCapabilityDeclaration",
    "ProviderClass",
    "ProviderInventoryRecord",
    "ProviderSnapshot",
    "ProviderStage",
]
