"""Provenance and action contracts for bounded search and multi-system control.

This module contains no network client and executes no external action. Discovery
records are untrusted evidence; control contracts must still pass CK-NEXUS policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from urllib.parse import urlsplit


class RightsBasis(StrEnum):
    PUBLIC_DOMAIN = "public_domain"
    OPEN_LICENSE = "open_license"
    USER_AUTHORIZED = "user_authorized"
    PROVIDER_TERMS = "provider_terms"
    UNKNOWN = "unknown"


class SourceTrust(StrEnum):
    UNVERIFIED = "unverified"
    OFFICIAL = "official"
    VERIFIED = "verified"


class DiscoveryDisposition(StrEnum):
    VERIFIED_CANDIDATE = "verified_candidate"
    DISCOVERY_ONLY = "discovery_only"
    STALE = "stale"
    BLOCKED = "blocked"


class ControlRisk(StrEnum):
    READ = "read"
    PLAN = "plan"
    SANDBOX_WRITE = "sandbox_write"
    CONTROLLED_WRITE = "controlled_write"
    DESTRUCTIVE = "destructive"


_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_WRITE_RISKS = frozenset(
    {ControlRisk.SANDBOX_WRITE, ControlRisk.CONTROLLED_WRITE, ControlRisk.DESTRUCTIVE}
)


def _aware_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class DiscoverySource:
    source_id: str
    url: str
    publisher: str
    fetched_at: str
    content_sha256: str
    rights_basis: RightsBasis = RightsBasis.UNKNOWN
    license_id: str | None = None
    rights_evidence_ref: str | None = None
    trust: SourceTrust = SourceTrust.UNVERIFIED
    version: str | None = None
    content_type: str = "text/html"

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not _ID.fullmatch(self.source_id):
            raise ValueError("source_id must be a stable identifier")
        if (
            not isinstance(self.publisher, str)
            or not self.publisher.strip()
            or len(self.publisher) > 256
        ):
            raise ValueError("publisher must be non-empty and at most 256 characters")
        if not isinstance(self.url, str) or len(self.url) > 2048:
            raise ValueError("source URL must be a string no longer than 2048 characters")
        parsed = urlsplit(self.url)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("discovery source must use HTTPS without embedded credentials")
        if not _SHA256.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be a 64-character SHA-256 digest")
        _aware_datetime(self.fetched_at, "fetched_at")
        if self.rights_basis is RightsBasis.OPEN_LICENSE and not self.license_id:
            raise ValueError("open-license sources require a license_id")
        if self.license_id is not None and len(self.license_id) > 128:
            raise ValueError("license_id exceeds 128 characters")
        if self.rights_basis is not RightsBasis.UNKNOWN and (
            not isinstance(self.rights_evidence_ref, str)
            or not _ID.fullmatch(self.rights_evidence_ref)
        ):
            raise ValueError("known rights require a stable rights_evidence_ref")
        if len(self.content_type) > 128:
            raise ValueError("content_type exceeds 128 characters")

    @property
    def rights_known(self) -> bool:
        return self.rights_basis is not RightsBasis.UNKNOWN

    @property
    def instructions_trusted(self) -> bool:
        """Fetched page text is always untrusted, even for an official publisher."""
        return False


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    candidate_id: str
    source_id: str
    capability: str
    title: str
    summary: str
    observed_at: str
    evidence_ref: str

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "source_id", "evidence_ref"):
            if not _ID.fullmatch(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be a stable identifier")
        for field_name, limit in (("capability", 128), ("title", 512), ("summary", 4000)):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{field_name} must be non-empty and at most {limit} characters")
        _aware_datetime(self.observed_at, "observed_at")


def assess_discovery_source(
    source: DiscoverySource,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(days=90),
) -> DiscoveryDisposition:
    """Classify evidence quality; unknown rights/trust never become installable."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if max_age.total_seconds() < 0:
        raise ValueError("max_age cannot be negative")
    fetched = _aware_datetime(source.fetched_at, "fetched_at")
    if fetched > current.astimezone(UTC) + timedelta(minutes=5):
        return DiscoveryDisposition.BLOCKED
    if current.astimezone(UTC) - fetched > max_age:
        return DiscoveryDisposition.STALE
    if not source.rights_known or source.trust is SourceTrust.UNVERIFIED:
        return DiscoveryDisposition.DISCOVERY_ONLY
    return DiscoveryDisposition.VERIFIED_CANDIDATE


@dataclass(frozen=True, slots=True)
class ControlActionContract:
    connector_id: str
    action_id: str
    required_scopes: frozenset[str]
    risk: ControlRisk
    max_timeout_seconds: int = 30
    evidence_types: tuple[str, ...] = ()
    rollback_supported: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.connector_id, str)
            or not _ID.fullmatch(self.connector_id)
            or not isinstance(self.action_id, str)
            or not _ID.fullmatch(self.action_id)
        ):
            raise ValueError("connector_id and action_id must be stable identifiers")
        if not self.required_scopes or any(
            not _ID.fullmatch(item) for item in self.required_scopes
        ):
            raise ValueError("at least one valid required scope is mandatory")
        if not 1 <= self.max_timeout_seconds <= 300:
            raise ValueError("max_timeout_seconds must be between 1 and 300")
        if len(self.evidence_types) > 20 or any(
            not _ID.fullmatch(item) for item in self.evidence_types
        ):
            raise ValueError("evidence_types must contain at most 20 stable identifiers")

    @property
    def approval_required(self) -> bool:
        return self.risk in _WRITE_RISKS

    @property
    def idempotency_required(self) -> bool:
        return self.risk in _WRITE_RISKS


@dataclass(frozen=True, slots=True)
class ControlActionRequest:
    connector_id: str
    action_id: str
    principal_id: str
    granted_scopes: frozenset[str]
    timeout_seconds: int = 30
    idempotency_key: str | None = None
    approval_ref: str | None = None
    owner_approval_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ControlDecision:
    allowed: bool
    reason: str
    connector_id: str
    action_id: str
    authority_level: str = "NONE"
    execution_performed: bool = False


def authorize_control_action(
    contract: ControlActionContract,
    request: ControlActionRequest,
    *,
    grant_verifier,
) -> ControlDecision:
    """Validate an exact action request; write grants are checked by injected authority.

    The verifier must validate and consume a one-time CK-NEXUS Core grant bound to
    this exact principal, connector, action, scopes, timeout and idempotency key.
    """

    def deny(reason: str) -> ControlDecision:
        return ControlDecision(False, reason, contract.connector_id, contract.action_id)

    if request.connector_id != contract.connector_id or request.action_id != contract.action_id:
        return deny("action_contract_mismatch")
    if not _ID.fullmatch(request.principal_id):
        return deny("trusted_principal_required")
    if not contract.required_scopes.issubset(request.granted_scopes):
        return deny("required_scope_missing")
    if not 1 <= request.timeout_seconds <= contract.max_timeout_seconds:
        return deny("timeout_out_of_bounds")
    if contract.idempotency_required and (
        not request.idempotency_key or not _ID.fullmatch(request.idempotency_key)
    ):
        return deny("idempotency_key_required")
    if contract.approval_required and not request.approval_ref:
        return deny("approval_reference_required")
    if contract.risk is ControlRisk.DESTRUCTIVE and not request.owner_approval_ref:
        return deny("owner_approval_required")
    if not callable(grant_verifier):
        return deny("trusted_grant_verifier_unavailable")
    try:
        verified = grant_verifier(contract=contract, request=request)
    except Exception:
        return deny("trusted_grant_verification_failed")
    if verified is not True:
        return deny("trusted_grant_denied")
    return ControlDecision(
        True,
        "policy_contract_validated_execution_not_performed",
        contract.connector_id,
        contract.action_id,
    )
