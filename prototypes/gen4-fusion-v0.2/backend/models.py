from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_VERIFIED = "NOT_VERIFIED"
    EXPIRED = "EXPIRED"


class VerificationLevel(str, Enum):
    SPEC_ONLY = "SPEC_ONLY"
    LOCAL = "LOCAL"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class ConnectorState(str, Enum):
    UNKNOWN = "UNKNOWN"
    DISCOVERED = "DISCOVERED"
    INSPECTED = "INSPECTED"
    SCANNED = "SCANNED"
    PENDING_AUTH = "PENDING_AUTH"
    ACTIVE_READONLY = "ACTIVE_READONLY"
    ACTIVE_READWRITE = "ACTIVE_READWRITE"
    BLOCKED = "BLOCKED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    REVOKED = "REVOKED"


class ApprovalDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class ReversibilityClass(str, Enum):
    R0_READ = "R0_READ"
    R1_TEMPORARY = "R1_TEMPORARY"
    R2_REVERSIBLE_WRITE = "R2_REVERSIBLE_WRITE"
    R3_EXTERNAL_WRITE = "R3_EXTERNAL_WRITE"
    R4_IRREVERSIBLE = "R4_IRREVERSIBLE"


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    subject: str
    source_commit: str
    tree_sha: str
    environment: str
    verification_level: VerificationLevel
    control_id: str
    status: EvidenceStatus
    observed_at: datetime
    stale_after: datetime | None = None
    test_id: str | None = None
    run_id: str | None = None
    artifact_digest: str | None = None
    supersedes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time_order(self) -> "EvidenceRecord":
        if self.stale_after is not None and self.stale_after <= self.observed_at:
            raise ValueError("stale_after must be later than observed_at")
        return self


class CapabilityLease(BaseModel):
    model_config = ConfigDict(frozen=True)

    lease_id: str
    subject_agent: str
    tenant: str
    allowed_actions: tuple[str, ...]
    resource_scope: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    allowed_tools: tuple[str, ...] = ()
    delegated_by: str | None = None
    max_calls: int | None = None
    max_cost: float | None = None
    max_mutations: int | None = None
    can_delegate: bool = False
    policy_hash: str | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "CapabilityLease":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        return self


class ConnectorRecord(BaseModel):
    connector_id: str
    name: str
    state: ConnectorState = ConnectorState.UNKNOWN
    activation: str = "NONE"
    protocol: str
    scopes: tuple[str, ...] = ()
    credential_ref: str | None = None
    approval_id: str | None = None
    last_evidence_id: str | None = None
    updated_at: datetime


class ApprovalRecord(BaseModel):
    approval_id: str
    tenant: str
    principal: str
    action: str
    resource: str
    reversibility: ReversibilityClass
    decision: ApprovalDecision = ApprovalDecision.PENDING
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    reason: str | None = None


class ExecutionEnvelope(BaseModel):
    execution_id: str
    tenant: str
    principal: str
    agent_id: str
    action: str
    resource: str
    tool_id: str
    subject: str
    policy_hash: str
    reversibility: ReversibilityClass
    capability_lease_id: str | None = None
    approval_id: str | None = None
    expected_effects: tuple[str, ...] = ()
    created_at: datetime


class ReleaseSnapshot(BaseModel):
    subject: str
    q10: EvidenceStatus = EvidenceStatus.NOT_VERIFIED
    q11: EvidenceStatus = EvidenceStatus.BLOCKED
    q12: EvidenceStatus = EvidenceStatus.BLOCKED
    reconciliation: EvidenceStatus = EvidenceStatus.NOT_VERIFIED
    final_package_success: bool = False
    artifact_checksum_verified: bool = False
