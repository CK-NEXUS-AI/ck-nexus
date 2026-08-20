"""CK-NEXUS migration contract for MCP specification 2026-07-28.

This module is intentionally transport-adapter logic only. It does not open sockets, authenticate
users, execute tools, or grant authority. It models the stateless request boundary that CK-NEXUS
will place in front of the existing read-only MCP server while compatibility is evaluated locally.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MCP_PROTOCOL_VERSION = "2026-07-28"
LEGACY_HANDSHAKE_METHODS = frozenset({"initialize", "notifications/initialized"})
LEGACY_SESSION_HEADERS = frozenset({"mcp-session-id", "mcp-session"})
SUPPORTED_TRANSPORTS = frozenset({"stdio", "streamable-http"})

_TOKEN = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
_SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")


class MCP2026ContractError(ValueError):
    """Raised when a request would violate the stateless MCP 2026-07-28 contract."""


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


def validate_transport(transport: str) -> str:
    """Allow only the non-legacy transports used by the CK-NEXUS migration profile."""
    normalized = transport.strip().lower()
    if normalized not in SUPPORTED_TRANSPORTS:
        raise MCP2026ContractError("legacy_or_unsupported_transport")
    return normalized


@dataclass(frozen=True, slots=True)
class MCP2026Request:
    """One self-contained MCP request with no protocol-level session dependency."""

    method: str
    name: str | None = None
    capabilities: tuple[str, ...] = ()
    task_id: str | None = None

    def validate(self) -> MCP2026Request:
        method = self.method.strip()
        if not _TOKEN.fullmatch(method):
            raise MCP2026ContractError("method_invalid")
        if method in LEGACY_HANDSHAKE_METHODS:
            raise MCP2026ContractError("legacy_initialize_handshake_denied")
        if self.name is not None and not _TOKEN.fullmatch(self.name.strip()):
            raise MCP2026ContractError("name_invalid")
        if len(self.capabilities) > 32:
            raise MCP2026ContractError("too_many_request_capabilities")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise MCP2026ContractError("duplicate_request_capability")
        for capability in self.capabilities:
            if not _TOKEN.fullmatch(capability.strip()):
                raise MCP2026ContractError("request_capability_invalid")
        if self.task_id is not None and not _SAFE_TASK_ID.fullmatch(self.task_id):
            raise MCP2026ContractError("task_id_invalid")
        return self

    def gateway_headers(self) -> dict[str, str]:
        """Build routing headers without creating any session identifier."""
        self.validate()
        headers = {
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            "Mcp-Method": self.method,
        }
        if self.name is not None:
            headers["Mcp-Name"] = self.name
        return headers

    def validate_gateway_headers(self, headers: Mapping[str, str]) -> None:
        """Fail closed on stale protocol/session routing or mismatched gateway metadata."""
        self.validate()
        normalized = _normalized_headers(headers)
        if LEGACY_SESSION_HEADERS.intersection(normalized):
            raise MCP2026ContractError("protocol_session_header_denied")
        if normalized.get("mcp-protocol-version") != MCP_PROTOCOL_VERSION:
            raise MCP2026ContractError("protocol_version_mismatch")
        if normalized.get("mcp-method") != self.method:
            raise MCP2026ContractError("mcp_method_header_mismatch")
        expected_name = self.name
        supplied_name = normalized.get("mcp-name")
        if expected_name is None:
            if supplied_name:
                raise MCP2026ContractError("unexpected_mcp_name_header")
        elif supplied_name != expected_name:
            raise MCP2026ContractError("mcp_name_header_mismatch")

    @property
    def cacheable_list_request(self) -> bool:
        """List requests are cache candidates only when they are not task-scoped."""
        self.validate()
        return self.method.endswith("/list") and self.task_id is None

    def cache_key(self, params: Mapping[str, Any] | None = None) -> str | None:
        """Return a deterministic cache key without persisting request payloads."""
        if not self.cacheable_list_request:
            return None
        canonical = json.dumps(
            {
                "protocol": MCP_PROTOCOL_VERSION,
                "method": self.method,
                "name": self.name,
                "capabilities": sorted(self.capabilities),
                "params": dict(params or {}),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "mcp-list-" + hashlib.sha256(canonical).hexdigest()

    def evidence_projection(self, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Emit bounded routing evidence; raw parameters are represented by digest only."""
        canonical_params = json.dumps(
            dict(params or {}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return {
            "protocol_version": MCP_PROTOCOL_VERSION,
            "method": self.method,
            "name": self.name,
            "capabilities": sorted(self.capabilities),
            "task_id": self.task_id,
            "params_sha256": hashlib.sha256(canonical_params).hexdigest(),
            "stateless": True,
            "legacy_initialize_allowed": False,
        }
