"""Tool and MCP capability trust registry for CK-NEXUS."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class ToolTrustState(StrEnum):
    UNKNOWN = "unknown"
    QUARANTINED = "quarantined"
    REVIEWED = "reviewed"
    TRUSTED_READ = "trusted_read"
    TRUSTED_WRITE = "trusted_write"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    tool_id: str
    provider: str
    version: str
    schema_hash: str
    source: str
    permissions: tuple[str, ...]
    network_domains: tuple[str, ...] = ()
    filesystem: str = "none"
    risk: str = "unknown"
    state: ToolTrustState = ToolTrustState.UNKNOWN

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.tool_id, self.provider, self.version, self.source)):
            raise ValueError("tool identity fields must not be empty")
        if len(self.schema_hash) != 64 or any(char not in "0123456789abcdef" for char in self.schema_hash):
            raise ValueError("schema_hash must be lowercase SHA-256")
        if "*" in self.network_domains:
            raise ValueError("wildcard network access is forbidden")


class ToolTrustDenied(PermissionError):
    """Raised when a tool is not trusted for the requested operation."""


class ToolTrustRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}

    def discover(self, descriptor: ToolDescriptor) -> ToolDescriptor:
        if descriptor.tool_id in self._tools:
            raise ValueError("tool_id already discovered")
        quarantined = replace(descriptor, state=ToolTrustState.QUARANTINED)
        self._tools[descriptor.tool_id] = quarantined
        return quarantined

    def set_state(self, tool_id: str, state: ToolTrustState) -> ToolDescriptor:
        current = self._tools[tool_id]
        if current.state == ToolTrustState.REVOKED and state != ToolTrustState.REVOKED:
            raise ToolTrustDenied("revoked tool cannot be reactivated")
        updated = replace(current, state=state)
        self._tools[tool_id] = updated
        return updated

    def require(self, tool_id: str, *, write: bool = False) -> ToolDescriptor:
        tool = self._tools[tool_id]
        accepted = {ToolTrustState.TRUSTED_WRITE} if write else {
            ToolTrustState.TRUSTED_READ,
            ToolTrustState.TRUSTED_WRITE,
        }
        if tool.state not in accepted:
            raise ToolTrustDenied("tool is not trusted for requested operation")
        return tool

    def get(self, tool_id: str) -> ToolDescriptor:
        return self._tools[tool_id]
