from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class Q11Status(StrEnum):
    DESIGNED = "DESIGNED"
    IMPLEMENTED = "IMPLEMENTED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    NOT_VERIFIED = "NOT_VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Q11ProviderResult(StrEnum):
    SUCCESS = "SUCCESS"
    INSUFFICIENT_QUOTA = "INSUFFICIENT_QUOTA"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNREACHABLE = "UNREACHABLE"
    OTHER_FAILURE = "OTHER_FAILURE"


@dataclass(frozen=True, slots=True)
class Q11GateResult:
    gate_id: str
    status: Q11Status
    provider: str | None = None
    execution_id: str | None = None
    release_id: str | None = None
    commit: str | None = None
    source_identity: str | None = None
    evidence_artifact: str | None = None
    evidence_sha256: str | None = None
    verification_method: str | None = None
    block_reason: str | None = None
    secret_redaction_status: str = "verified_no_secrets"


_REQUIRED_METADATA = (
    "execution_id",
    "release_id",
    "commit",
    "source_identity",
    "evidence_artifact",
    "evidence_sha256",
    "verification_method",
)


def validate_gate_evidence(gate: Q11GateResult) -> None:
    if not gate.gate_id.startswith("Q11-"):
        raise ValueError("gate_id must identify a Q11 sub-gate")
    if gate.status is Q11Status.VERIFIED:
        missing = [field for field in _REQUIRED_METADATA if not getattr(gate, field)]
        if missing:
            raise ValueError("VERIFIED Q11 evidence requires: " + ", ".join(missing))
        if gate.secret_redaction_status != "verified_no_secrets":
            raise ValueError("VERIFIED Q11 evidence must confirm secret redaction")
        if gate.verification_method.lower().find("mock") >= 0:
            raise ValueError("mock verification cannot produce VERIFIED status")
        if not gate.evidence_sha256.startswith("sha256:"):
            raise ValueError("VERIFIED Q11 evidence requires a SHA-256 artifact digest")


def classify_provider_result(
    *, http_status: int | None, error_code: str | None = None
) -> Q11ProviderResult:
    code = (error_code or "").strip().lower()
    if code == "insufficient_quota" or http_status == 429:
        return Q11ProviderResult.INSUFFICIENT_QUOTA
    if http_status in {401, 403}:
        return Q11ProviderResult.UNAUTHORIZED
    if http_status is None:
        return Q11ProviderResult.UNREACHABLE
    if 200 <= http_status < 300:
        return Q11ProviderResult.SUCCESS
    return Q11ProviderResult.OTHER_FAILURE


def provider_gate_status(
    *,
    provider: str,
    http_status: int | None,
    error_code: str | None,
    sentinel_observed: bool,
    verification_method: str,
) -> tuple[Q11Status, Q11Status, str | None]:
    result = classify_provider_result(http_status=http_status, error_code=error_code)
    if result is Q11ProviderResult.SUCCESS and sentinel_observed:
        return Q11Status.VERIFIED, Q11Status.VERIFIED, None
    if result is Q11ProviderResult.INSUFFICIENT_QUOTA:
        return Q11Status.BLOCKED, Q11Status.BLOCKED, f"{provider}: insufficient_quota"
    if result is Q11ProviderResult.UNAUTHORIZED:
        return Q11Status.BLOCKED, Q11Status.NOT_VERIFIED, f"{provider}: unauthorized"
    if result is Q11ProviderResult.UNREACHABLE:
        return Q11Status.BLOCKED, Q11Status.NOT_VERIFIED, f"{provider}: unreachable"
    if result is Q11ProviderResult.SUCCESS and not sentinel_observed:
        return (
            Q11Status.EXECUTED,
            Q11Status.NOT_VERIFIED,
            f"{provider}: live response missing required sentinel",
        )
    return Q11Status.BLOCKED, Q11Status.NOT_VERIFIED, f"{provider}: live provider failure"


def aggregate_q11(
    gates: Mapping[str, Q11GateResult], *, authoritative_provider: str = "openai"
) -> Q11Status:
    required = ("Q11-A", "Q11-B", "Q11-C", "Q11-D", "Q11-E", "Q11-F", "Q11-G")
    if any(gate_id not in gates for gate_id in required):
        return Q11Status.NOT_VERIFIED

    for gate in gates.values():
        validate_gate_evidence(gate)

    provider_gates = [
        gate
        for gate in gates.values()
        if gate.provider == authoritative_provider
        and gate.gate_id in {"Q11-C", "Q11-D", "Q11-E", "Q11-F"}
    ]
    if not provider_gates:
        return Q11Status.NOT_VERIFIED
    if any(gate.status is Q11Status.BLOCKED for gate in provider_gates):
        return Q11Status.BLOCKED
    if any(
        gate.status not in {Q11Status.VERIFIED, Q11Status.NOT_APPLICABLE} for gate in gates.values()
    ):
        return Q11Status.NOT_VERIFIED
    return Q11Status.VERIFIED


def make_gate(
    gate_id: str,
    status: Q11Status,
    *,
    provider: str | None = None,
    execution_id: str = "not-applicable",
    release_id: str = "not-applicable",
    commit: str = "not-applicable",
    source_identity: str = "not-applicable",
    evidence_artifact: str = "not-applicable",
    evidence_sha256: str = "sha256:not-applicable",
    verification_method: str = "not-applicable",
    block_reason: str | None = None,
) -> Q11GateResult:
    return Q11GateResult(
        gate_id=gate_id,
        status=status,
        provider=provider,
        execution_id=execution_id,
        release_id=release_id,
        commit=commit,
        source_identity=source_identity,
        evidence_artifact=evidence_artifact,
        evidence_sha256=evidence_sha256,
        verification_method=verification_method,
        block_reason=block_reason,
    )
