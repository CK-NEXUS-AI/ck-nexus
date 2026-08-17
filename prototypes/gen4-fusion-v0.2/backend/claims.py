from __future__ import annotations

from .models import EvidenceStatus, ReleaseSnapshot


def production_ready(snapshot: ReleaseSnapshot) -> bool:
    return (
        snapshot.q10 is EvidenceStatus.PASS
        and snapshot.q11 is EvidenceStatus.PASS
        and snapshot.q12 is EvidenceStatus.PASS
        and snapshot.reconciliation is EvidenceStatus.PASS
        and snapshot.final_package_success
        and snapshot.artifact_checksum_verified
    )


def compile_public_claims(snapshot: ReleaseSnapshot) -> dict[str, object]:
    ready = production_ready(snapshot)
    allowed = [
        "Evidence-first architecture",
        "Fail-closed release policy",
        "Connector state model with read-only default",
    ]
    blocked: list[str] = []
    if ready:
        allowed.append("Production Ready")
    else:
        blocked.extend(["Production Ready", "Production Verified", "All production gates passed"])
    return {
        "subject": snapshot.subject,
        "commercial_classification": "SELLABLE_SOURCE_BETA" if not ready else "RELEASE_ELIGIBLE",
        "production_classification": "READY" if ready else "NO_GO",
        "allowed_claims": allowed,
        "blocked_claims": blocked,
    }
