"""Fail-closed policy for remote/mobile device bridges."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BridgeCapability(StrEnum):
    """Capabilities a device bridge may request."""

    READ_ONLY = "read_only"
    FILE_WRITE = "file_write"
    SYSTEM_EXEC = "system_exec"
    CREDENTIAL_ACCESS = "credential_access"
    PRODUCTION_MUTATION = "production_mutation"


@dataclass(frozen=True)
class BridgeDecision:
    """Auditable bridge policy decision."""

    allowed: bool
    reason: str
    package_id: str
    capability: BridgeCapability
    exact_build_verified: bool


QUARANTINED_PACKAGE_IDS = frozenset({"gptos.intelligence.assistant"})


def evaluate_bridge(
    *,
    package_id: str,
    capability: BridgeCapability,
    exact_build_verified: bool,
) -> BridgeDecision:
    """Return a fail-closed decision for one requested bridge capability."""
    normalized = package_id.strip()
    if not normalized:
        return BridgeDecision(
            allowed=False,
            reason="missing_package_id",
            package_id=normalized,
            capability=capability,
            exact_build_verified=exact_build_verified,
        )

    if normalized in QUARANTINED_PACKAGE_IDS:
        return BridgeDecision(
            allowed=False,
            reason="package_quarantined",
            package_id=normalized,
            capability=capability,
            exact_build_verified=exact_build_verified,
        )

    if not exact_build_verified:
        return BridgeDecision(
            allowed=False,
            reason="exact_build_not_verified",
            package_id=normalized,
            capability=capability,
            exact_build_verified=exact_build_verified,
        )

    if capability is not BridgeCapability.READ_ONLY:
        return BridgeDecision(
            allowed=False,
            reason="mutation_or_sensitive_capability_denied",
            package_id=normalized,
            capability=capability,
            exact_build_verified=exact_build_verified,
        )

    return BridgeDecision(
        allowed=True,
        reason="verified_read_only_bridge",
        package_id=normalized,
        capability=capability,
        exact_build_verified=exact_build_verified,
    )
