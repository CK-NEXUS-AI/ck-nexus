"""Deterministic capability attestation and behavioral fingerprint primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .contracts import AttestationState, ModelCapability, ModelDescriptor


@dataclass(frozen=True, slots=True)
class CapabilityCheck:
    capability: ModelCapability
    passed: bool
    evidence_id: str = ""
    metric: float | None = None


@dataclass(frozen=True, slots=True)
class CapabilityAttestation:
    state: AttestationState
    measured_capabilities: frozenset[ModelCapability]
    evidence_ids: tuple[str, ...]
    digest: str


def attest_capabilities(
    model: ModelDescriptor,
    checks: tuple[CapabilityCheck, ...],
) -> CapabilityAttestation:
    """Build an immutable attestation from explicit checks.

    VERIFIED requires every claimed capability to have a passing check with an evidence id.
    Partial passing evidence is MEASURED. No passing checks remains CLAIMED.
    """

    passed = {check.capability for check in checks if check.passed}
    evidence_ids = tuple(sorted({check.evidence_id for check in checks if check.evidence_id}))
    claimed = set(model.capabilities)

    if claimed and claimed.issubset(passed) and all(
        check.evidence_id for check in checks if check.capability in claimed and check.passed
    ):
        state = AttestationState.VERIFIED
    elif passed:
        state = AttestationState.MEASURED
    else:
        state = AttestationState.CLAIMED

    payload = {
        "provider_id": model.provider_id,
        "model_id": model.model_id,
        "runtime_id": model.runtime_id,
        "claimed": sorted(cap.value for cap in model.capabilities),
        "measured": sorted(cap.value for cap in passed),
        "evidence_ids": evidence_ids,
        "state": state.value,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CapabilityAttestation(state, frozenset(passed), evidence_ids, digest)


def behavioral_fingerprint(
    model: ModelDescriptor,
    metrics: dict[str, Any],
) -> str:
    """Create a stable fingerprint over model identity, provenance and measured metrics."""

    safe_metrics = {
        str(key): value
        for key, value in sorted(metrics.items())
        if isinstance(value, (str, int, float, bool, type(None)))
    }
    payload = {
        "provider_id": model.provider_id,
        "model_id": model.model_id,
        "runtime_id": model.runtime_id,
        "revision_sha": model.provenance.revision_sha,
        "weight_digest": model.provenance.weight_digest,
        "quantization": model.provenance.quantization,
        "metrics": safe_metrics,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
