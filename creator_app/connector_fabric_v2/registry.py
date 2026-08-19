"""Normalized connector lifecycle and capability registry for CK-NEXUS."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class ConnectorState(StrEnum):
    DISCOVERED = "discovered"
    CONFIGURED = "configured"
    AUTHENTICATED = "authenticated"
    AUTHORIZED = "authorized"
    HEALTHY = "healthy"
    AVAILABLE = "available"
    REVOKED = "revoked"


class CapabilityMode(StrEnum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class ConnectorCapability:
    capability_id: str
    mode: CapabilityMode
    risk: str = "low"


@dataclass(frozen=True, slots=True)
class ConnectorRecord:
    connector_id: str
    provider: str
    tenant_id: str
    state: ConnectorState
    capabilities: tuple[ConnectorCapability, ...] = ()
    scopes: tuple[str, ...] = ()
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.connector_id.strip() or not self.provider.strip() or not self.tenant_id.strip():
            raise ValueError("connector identity fields must not be empty")
        if self.credential_ref is not None and not self.credential_ref.startswith("cred://"):
            raise ValueError("credential_ref must be an opaque cred:// reference")


_ALLOWED_TRANSITIONS: dict[ConnectorState, frozenset[ConnectorState]] = {
    ConnectorState.DISCOVERED: frozenset({ConnectorState.CONFIGURED, ConnectorState.REVOKED}),
    ConnectorState.CONFIGURED: frozenset({ConnectorState.AUTHENTICATED, ConnectorState.REVOKED}),
    ConnectorState.AUTHENTICATED: frozenset({ConnectorState.AUTHORIZED, ConnectorState.REVOKED}),
    ConnectorState.AUTHORIZED: frozenset({ConnectorState.HEALTHY, ConnectorState.REVOKED}),
    ConnectorState.HEALTHY: frozenset({ConnectorState.AVAILABLE, ConnectorState.REVOKED}),
    ConnectorState.AVAILABLE: frozenset({ConnectorState.HEALTHY, ConnectorState.REVOKED}),
    ConnectorState.REVOKED: frozenset(),
}


class ConnectorLifecycleError(ValueError):
    """Raised for invalid connector lifecycle transitions."""


class ConnectorRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ConnectorRecord] = {}

    def add(self, record: ConnectorRecord) -> None:
        if record.connector_id in self._records:
            raise ValueError("connector_id already registered")
        if record.state != ConnectorState.DISCOVERED:
            raise ConnectorLifecycleError("new connector must start DISCOVERED")
        self._records[record.connector_id] = record

    def transition(self, connector_id: str, state: ConnectorState) -> ConnectorRecord:
        current = self._records[connector_id]
        if state not in _ALLOWED_TRANSITIONS[current.state]:
            raise ConnectorLifecycleError(
                f"invalid connector transition: {current.state.value} -> {state.value}"
            )
        updated = replace(current, state=state)
        self._records[connector_id] = updated
        return updated

    def bind_authorization(
        self,
        connector_id: str,
        *,
        scopes: tuple[str, ...],
        capabilities: tuple[ConnectorCapability, ...],
        credential_ref: str,
    ) -> ConnectorRecord:
        current = self._records[connector_id]
        if current.state != ConnectorState.AUTHENTICATED:
            raise ConnectorLifecycleError("connector must be AUTHENTICATED before authorization")
        if not credential_ref.startswith("cred://"):
            raise ValueError("credential_ref must be an opaque cred:// reference")
        updated = replace(
            current,
            state=ConnectorState.AUTHORIZED,
            scopes=tuple(sorted(set(scopes))),
            capabilities=capabilities,
            credential_ref=credential_ref,
        )
        self._records[connector_id] = updated
        return updated

    def capability_allowed(
        self,
        connector_id: str,
        capability_id: str,
        *,
        mode: CapabilityMode,
    ) -> bool:
        record = self._records[connector_id]
        if record.state != ConnectorState.AVAILABLE:
            return False
        return any(
            item.capability_id == capability_id and item.mode == mode
            for item in record.capabilities
        )

    def get(self, connector_id: str) -> ConnectorRecord:
        return self._records[connector_id]
