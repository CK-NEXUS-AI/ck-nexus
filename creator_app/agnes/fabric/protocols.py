"""Protocol-neutral capability gateway descriptors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtocolDescriptor:
    protocol_id: str
    stateless_preferred: bool
    supports_discovery: bool
    requires_reauthorization_on_handoff: bool


PROTOCOLS: tuple[ProtocolDescriptor, ...] = (
    ProtocolDescriptor("MCP", True, True, False),
    ProtocolDescriptor("A2A", True, True, True),
    ProtocolDescriptor("REST", True, False, False),
    ProtocolDescriptor("OPENAPI", True, False, False),
    ProtocolDescriptor("OAUTH", True, False, False),
    ProtocolDescriptor("WEBHOOK", True, False, False),
    ProtocolDescriptor("NATIVE", False, False, False),
)
