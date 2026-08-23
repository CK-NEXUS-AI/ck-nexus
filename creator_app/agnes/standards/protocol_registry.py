from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CompatibilityResult(str, Enum):
    CURRENT = "CURRENT"
    COMPATIBLE_LEGACY = "COMPATIBLE_LEGACY"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ProtocolSpec:
    name: str
    latest_version: str
    minimum_supported_version: str
    notes: tuple[str, ...] = ()


class ProtocolRegistry:
    """Authoritative protocol facts for development/runtime negotiation.

    This registry intentionally separates protocol discovery from execution authority.
    A compatible protocol version never grants tool or agent permissions by itself.
    """

    _SPECS = {
        "mcp": ProtocolSpec(
            name="mcp",
            latest_version="2026-07-28",
            minimum_supported_version="2025-11-25",
            notes=(
                "latest core is stateless request/response",
                "do not require handshake/session affinity",
                "support header-aware routing and cacheable list results",
                "treat Tasks and MCP Apps as extensions, not implicit core authority",
            ),
        ),
        "a2a": ProtocolSpec(
            name="a2a",
            latest_version="1.0.0",
            minimum_supported_version="0.3.0",
            notes=(
                "negotiate capabilities and modalities using Agent Cards",
                "task/message/artifact lifecycle is protocol state, not CK execution authority",
                "validation/TCK evidence should be tracked separately from runtime trust",
            ),
        ),
    }

    @classmethod
    def get(cls, name: str) -> ProtocolSpec:
        key = name.strip().lower()
        if key not in cls._SPECS:
            raise KeyError(f"unknown protocol: {name}")
        return cls._SPECS[key]

    @classmethod
    def compatibility(cls, name: str, version: str) -> CompatibilityResult:
        spec = cls.get(name)
        if version == spec.latest_version:
            return CompatibilityResult.CURRENT
        if name.lower() == "mcp" and version == "2025-11-25":
            return CompatibilityResult.MIGRATION_REQUIRED
        if name.lower() == "a2a" and version == "0.3.0":
            return CompatibilityResult.COMPATIBLE_LEGACY
        return CompatibilityResult.UNSUPPORTED
