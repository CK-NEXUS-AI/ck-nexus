from __future__ import annotations

from datetime import datetime, timezone
from .models import ConnectorRecord, ConnectorState


LEGAL_TRANSITIONS: dict[ConnectorState, set[ConnectorState]] = {
    ConnectorState.UNKNOWN: {ConnectorState.DISCOVERED},
    ConnectorState.DISCOVERED: {ConnectorState.INSPECTED, ConnectorState.BLOCKED, ConnectorState.ERROR},
    ConnectorState.INSPECTED: {ConnectorState.SCANNED, ConnectorState.BLOCKED, ConnectorState.ERROR},
    ConnectorState.SCANNED: {ConnectorState.PENDING_AUTH, ConnectorState.BLOCKED, ConnectorState.ERROR},
    ConnectorState.PENDING_AUTH: {ConnectorState.ACTIVE_READONLY, ConnectorState.BLOCKED, ConnectorState.ERROR, ConnectorState.REVOKED},
    ConnectorState.ACTIVE_READONLY: {ConnectorState.ACTIVE_READWRITE, ConnectorState.DISCONNECTED, ConnectorState.REVOKED, ConnectorState.ERROR},
    ConnectorState.ACTIVE_READWRITE: {ConnectorState.ACTIVE_READONLY, ConnectorState.DISCONNECTED, ConnectorState.REVOKED, ConnectorState.ERROR},
    ConnectorState.BLOCKED: {ConnectorState.INSPECTED, ConnectorState.REVOKED},
    ConnectorState.DISCONNECTED: {ConnectorState.PENDING_AUTH, ConnectorState.REVOKED},
    ConnectorState.ERROR: {ConnectorState.INSPECTED, ConnectorState.REVOKED},
    ConnectorState.REVOKED: set(),
}


class IllegalConnectorTransition(ValueError):
    pass


def transition(
    record: ConnectorRecord,
    target: ConnectorState,
    *,
    evidence_id: str | None = None,
    credential_ref: str | None = None,
    approval_id: str | None = None,
) -> ConnectorRecord:
    if target not in LEGAL_TRANSITIONS[record.state]:
        raise IllegalConnectorTransition(f"{record.state} -> {target} is not allowed")

    # Authorization cannot be inferred from UI state.
    if target in {ConnectorState.ACTIVE_READONLY, ConnectorState.ACTIVE_READWRITE}:
        if not evidence_id or not credential_ref:
            raise IllegalConnectorTransition("activation requires provider-bound evidence and credential reference")

    # Write mode additionally requires explicit approval reference.
    if target is ConnectorState.ACTIVE_READWRITE and not approval_id:
        raise IllegalConnectorTransition("write activation requires explicit approval reference")

    activation = {
        ConnectorState.ACTIVE_READONLY: "READ_ONLY",
        ConnectorState.ACTIVE_READWRITE: "READ_WRITE",
    }.get(target, "NONE")

    return record.model_copy(update={
        "state": target,
        "activation": activation,
        "credential_ref": credential_ref or record.credential_ref,
        "approval_id": approval_id or record.approval_id,
        "last_evidence_id": evidence_id or record.last_evidence_id,
        "updated_at": datetime.now(timezone.utc),
    })
