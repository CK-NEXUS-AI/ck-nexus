from __future__ import annotations

from datetime import datetime, timezone
from .models import ApprovalDecision, ApprovalRecord, CapabilityLease, ReversibilityClass


def lease_is_active(lease: CapabilityLease, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return lease.issued_at <= now < lease.expires_at


def lease_allows(lease: CapabilityLease, action: str, resource: str, *, now: datetime | None = None) -> bool:
    if not lease_is_active(lease, now=now):
        return False
    if action not in lease.allowed_actions:
        return False
    return any(resource == scope or resource.startswith(scope.rstrip("/") + "/") for scope in lease.resource_scope)


def approval_required(reversibility: ReversibilityClass) -> bool:
    return reversibility in {ReversibilityClass.R3_EXTERNAL_WRITE, ReversibilityClass.R4_IRREVERSIBLE}


def approval_is_valid(approval: ApprovalRecord | None, *, now: datetime | None = None) -> bool:
    if approval is None:
        return False
    now = now or datetime.now(timezone.utc)
    return approval.decision is ApprovalDecision.APPROVED and now < approval.expires_at
