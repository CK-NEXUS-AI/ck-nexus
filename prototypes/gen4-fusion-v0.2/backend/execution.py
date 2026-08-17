from __future__ import annotations

from .models import ApprovalRecord, CapabilityLease, ExecutionEnvelope
from .policy import approval_is_valid, approval_required, lease_allows


class ExecutionDenied(PermissionError):
    pass


def authorize_execution(
    envelope: ExecutionEnvelope,
    lease: CapabilityLease | None,
    approval: ApprovalRecord | None,
) -> None:
    if lease is None or envelope.capability_lease_id != lease.lease_id:
        raise ExecutionDenied("missing or mismatched capability lease")
    if not lease_allows(lease, envelope.action, envelope.resource):
        raise ExecutionDenied("capability lease does not allow this action/resource")
    if approval_required(envelope.reversibility):
        if not approval_is_valid(approval) or envelope.approval_id != approval.approval_id:
            raise ExecutionDenied("valid explicit approval is required")
