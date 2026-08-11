from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ConnectorProtocol(StrEnum):
    MCP = "mcp"
    OPENAPI = "openapi"


class ConnectorState(StrEnum):
    REGISTERED = "REGISTERED"
    DISCOVERED = "DISCOVERED"
    SCHEMA_VERIFIED = "SCHEMA_VERIFIED"
    POLICY_APPROVED = "POLICY_APPROVED"
    ACTIVE_READ_ONLY = "ACTIVE_READ_ONLY"
    ACTIVE_WRITE = "ACTIVE_WRITE"
    BLOCKED = "BLOCKED"


class RiskClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    connector_id: str
    url: str
    protocol: ConnectorProtocol
    credential_ref: str | None = None
    trust_source: str = "manual"
    allow_private_network: bool = False
    allowed_tools: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "connectorId": self.connector_id,
            "url": self.url,
            "protocol": self.protocol.value,
            "credentialRef": self.credential_ref,
            "trustSource": self.trust_source,
            "allowPrivateNetwork": self.allow_private_network,
            "allowedTools": list(self.allowed_tools),
        }


@dataclass(frozen=True, slots=True)
class NormalizedTool:
    connector_id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] = field(default_factory=dict)
    risk: RiskClass = RiskClass.UNKNOWN
    source_method: str | None = None
    source_path: str | None = None

    @property
    def logical_name(self) -> str:
        return f"{self.connector_id}.{self.name}"

    @property
    def read_only(self) -> bool:
        return self.risk is RiskClass.READ_ONLY

    @property
    def approval_required(self) -> bool:
        return self.risk is not RiskClass.READ_ONLY

    def as_dict(self) -> dict[str, Any]:
        return {
            "connectorId": self.connector_id,
            "name": self.name,
            "logicalName": self.logical_name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "annotations": self.annotations,
            "risk": self.risk.value,
            "readOnly": self.read_only,
            "approvalRequired": self.approval_required,
            "sourceMethod": self.source_method,
            "sourcePath": self.source_path,
        }


@dataclass(frozen=True, slots=True)
class DiscoverySnapshot:
    connector_id: str
    protocol: ConnectorProtocol
    protocol_version: str | None
    tools: tuple[NormalizedTool, ...]
    resources: tuple[dict[str, Any], ...] = ()
    prompts: tuple[dict[str, Any], ...] = ()
    capabilities: dict[str, Any] = field(default_factory=dict)
    schema_hash: str = ""
    cache_ttl_ms: int | None = None
    cache_scope: str | None = None
    rejected_tools: tuple[dict[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "connectorId": self.connector_id,
            "url": self.url,
            "protocol": self.protocol.value,
            "protocolVersion": self.protocol_version,
            "schemaHash": self.schema_hash,
            "cacheTtlMs": self.cache_ttl_ms,
            "cacheScope": self.cache_scope,
            "capabilities": self.capabilities,
            "tools": [tool.as_dict() for tool in self.tools],
            "resources": list(self.resources),
            "prompts": list(self.prompts),
            "rejectedTools": list(self.rejected_tools),
        }


@dataclass(frozen=True, slots=True)
class ConnectorRecord:
    config: ConnectorConfig
    state: ConnectorState = ConnectorState.REGISTERED
    schema_hash: str = ""
    tool_count: int = 0
    read_only_count: int = 0
    write_count: int = 0
    destructive_count: int = 0
    blocked_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.config.public_dict(),
            "state": self.state.value,
            "schemaHash": self.schema_hash,
            "toolCount": self.tool_count,
            "readOnlyCount": self.read_only_count,
            "writeCount": self.write_count,
            "destructiveCount": self.destructive_count,
            "blockedReason": self.blocked_reason,
        }
