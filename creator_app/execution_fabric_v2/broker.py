"""Fail-closed capability and network broker for Execution Fabric V2."""

from __future__ import annotations

from .contracts import (
    CapabilityLease,
    ExecutionAction,
    ExecutionAuthorization,
    ExecutionProposal,
)


class ExecutionDenied(PermissionError):
    """Raised when a proposal is outside its capability lease."""


class ExecutionPolicyBroker:
    """Consume short-lived leases without revealing credential material."""

    def __init__(self) -> None:
        self._uses: dict[str, int] = {}

    def authorize(
        self,
        proposal: ExecutionProposal,
        lease: CapabilityLease,
    ) -> ExecutionAuthorization:
        if not lease.active:
            raise ExecutionDenied("capability lease is expired")
        if proposal.capability != lease.capability:
            raise ExecutionDenied("proposal capability does not match lease")
        if proposal.scope != lease.scope:
            raise ExecutionDenied("proposal scope does not match lease")

        used = self._uses.get(lease.lease_id, 0)
        if used >= lease.max_actions:
            raise ExecutionDenied("capability lease action budget exhausted")

        network_allowed = proposal.destination_domain is None
        if proposal.destination_domain is not None:
            destination = proposal.destination_domain.casefold().strip(".")
            network_allowed = destination in {
                domain.casefold().strip(".") for domain in lease.network_domains
            }
            if not network_allowed:
                raise ExecutionDenied("destination domain is not allowlisted")

        if proposal.action in {ExecutionAction.EXTERNAL_WRITE, ExecutionAction.DESTRUCTIVE}:
            if not proposal.user_approved:
                raise ExecutionDenied("external/destructive action requires explicit user approval")

        if proposal.action == ExecutionAction.PRODUCTION_MUTATION:
            if not proposal.user_approved or not lease.release_authorized:
                raise ExecutionDenied(
                    "production mutation requires user approval and release-authorized lease"
                )

        if proposal.action == ExecutionAction.PATCH_CREATE and not proposal.patch_only:
            raise ExecutionDenied("development mutation must remain patch-only")

        self._uses[lease.lease_id] = used + 1
        return ExecutionAuthorization(
            allowed=True,
            reason="capability_lease_authorized",
            lease_id=lease.lease_id,
            capability=lease.capability,
            scope=lease.scope,
            network_allowed=network_allowed,
            credential_refs=lease.credential_refs,
            patch_only=proposal.patch_only,
        )

    def remaining_actions(self, lease: CapabilityLease) -> int:
        return max(0, lease.max_actions - self._uses.get(lease.lease_id, 0))
