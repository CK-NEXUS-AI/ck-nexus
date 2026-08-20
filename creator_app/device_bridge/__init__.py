"""Governed device bridge primitives for CK-NEXUS."""

from .descriptor import (
    ConnectionDescriptor,
    DescriptorError,
    connection_fingerprint,
    parse_descriptor,
    validate_registry_match,
)
from .policy import BridgeCapability, BridgeDecision, evaluate_bridge

__all__ = [
    "BridgeCapability",
    "BridgeDecision",
    "ConnectionDescriptor",
    "DescriptorError",
    "connection_fingerprint",
    "evaluate_bridge",
    "parse_descriptor",
    "validate_registry_match",
]
