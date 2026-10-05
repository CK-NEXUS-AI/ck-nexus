from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from .request import SkillExecutionRequest


class OmniGateError(PermissionError):
    """Raised when an OMNI execution contract cannot be proven safe."""


class RiskDecision(StrEnum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    SANDBOX_ONLY = "SANDBOX_ONLY"


class EvidenceLevel(StrEnum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    agent_id: str
    model_id: str
    issuer: str
    identity_ref: str


@dataclass(frozen=True, slots=True)
class CapabilityLease:
    lease_id: str
    agent_id: str
    capabilities: tuple[str, ...]
    issued_at: float
    expires_at: float
    revocation_ref: str | None = None

    def active(self, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        return self.expires_at > current >= self.issued_at

    def permits(self, capability: str, now: float | None = None) -> bool:
        return self.active(now) and capability in self.capabilities


@dataclass(frozen=True, slots=True)
class PreExecutionRiskVerdict:
    risk_verdict_id: str
    execution_id: str
    agent_id: str
    capability_id: str
    policy_id: str
    decision: RiskDecision
    risk: EvidenceLevel
    blast_radius: str
    reversibility: str
    data_sensitivity: str
    external_side_effect: bool


@dataclass(frozen=True, slots=True)
class DelegationContext:
    parent_execution_id: str
    parent_agent_id: str
    delegated_capabilities: tuple[str, ...]
    child_agent_id: str


@dataclass(frozen=True, slots=True)
class OMNIActionRecord:
    execution_id: str
    intent_id: str
    agent_id: str
    model_id: str
    capability_id: str
    policy_id: str
    risk_verdict_id: str
    lease_id: str
    tool_id: str
    target_id: str
    input_hash: str
    output_hash: str | None
    runtime_id: str
    verifier_id: str
    evidence_id: str | None
    parent_execution_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OMNIExecutionContext:
    identity: AgentIdentity
    capability_id: str
    lease: CapabilityLease
    policy_id: str
    risk_verdict: PreExecutionRiskVerdict
    tool_id: str
    target_id: str
    runtime_id: str
    verifier_id: str
    evidence_required: bool = True
    intent_id: str = ""
    delegation: DelegationContext | None = None

    def validate(self, request: SkillExecutionRequest) -> None:
        if not self.identity.agent_id or not self.identity.model_id or not self.identity.issuer:
            raise OmniGateError("agent_identity_missing")
        if not self.identity.identity_ref:
            raise OmniGateError("agent_identity_proof_missing")
        if not self.capability_id:
            raise OmniGateError("capability_id_missing")
        if not self.policy_id:
            raise OmniGateError("policy_id_missing")
        if not self.lease.lease_id or self.lease.agent_id != self.identity.agent_id:
            raise OmniGateError("capability_lease_identity_mismatch")
        if self.lease.revocation_ref:
            raise OmniGateError("capability_lease_revoked")
        if not self.lease.active():
            raise OmniGateError("capability_lease_expired_or_inactive")
        if not self.lease.permits(self.capability_id):
            raise OmniGateError("capability_outside_lease_scope")
        if self.risk_verdict.execution_id != request.execution_id:
            raise OmniGateError("risk_verdict_execution_mismatch")
        if self.risk_verdict.agent_id != self.identity.agent_id:
            raise OmniGateError("risk_verdict_agent_mismatch")
        if self.risk_verdict.capability_id != self.capability_id:
            raise OmniGateError("risk_verdict_capability_mismatch")
        if self.risk_verdict.policy_id != self.policy_id:
            raise OmniGateError("risk_verdict_policy_mismatch")
        if self.risk_verdict.decision in {
            RiskDecision.BLOCK,
            RiskDecision.SANDBOX_ONLY,
            RiskDecision.WARN,
            RiskDecision.REQUIRE_APPROVAL,
        }:
            if self.risk_verdict.decision is RiskDecision.REQUIRE_APPROVAL and request.approval_id:
                pass
            else:
                raise OmniGateError(f"risk_verdict_not_allow:{self.risk_verdict.decision.value}")
        if not self.tool_id or not self.target_id:
            raise OmniGateError("tool_target_binding_missing")
        declared_tool = request.plan_step.get("tool_id")
        declared_target = request.plan_step.get("target_id")
        if declared_tool is not None and declared_tool != self.tool_id:
            raise OmniGateError("tool_binding_mismatch")
        if declared_target is not None and declared_target != self.target_id:
            raise OmniGateError("target_binding_mismatch")
        if not self.runtime_id:
            raise OmniGateError("runtime_binding_missing")
        if not self.verifier_id:
            raise OmniGateError("verifier_binding_missing")
        if self.evidence_required is not True:
            raise OmniGateError("evidence_requirement_missing")
        if request.environment == "production" and self.risk_verdict.risk is not EvidenceLevel.E0:
            raise OmniGateError("production_mutation_requires_governed_read_only_verdict")
        if self.delegation is not None:
            if not self.delegation.parent_execution_id:
                raise OmniGateError("delegation_parent_execution_id_missing")
            if self.delegation.child_agent_id != self.identity.agent_id:
                raise OmniGateError("delegation_child_identity_mismatch")
            if not set(request.granted_capabilities).issubset(
                set(self.delegation.delegated_capabilities)
            ):
                raise OmniGateError("delegated_capability_escalation")

    def action_record(
        self,
        request: SkillExecutionRequest,
        *,
        output_hash: str | None = None,
        evidence_id: str | None = None,
    ) -> OMNIActionRecord:
        self.validate(request)
        input_hash = hashlib.sha256(
            json.dumps(
                request.inputs,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return OMNIActionRecord(
            execution_id=request.execution_id,
            intent_id=self.intent_id or request.correlation_id,
            agent_id=self.identity.agent_id,
            model_id=self.identity.model_id,
            capability_id=self.capability_id,
            policy_id=self.policy_id,
            risk_verdict_id=self.risk_verdict.risk_verdict_id,
            lease_id=self.lease.lease_id,
            tool_id=self.tool_id,
            target_id=self.target_id,
            input_hash=input_hash,
            output_hash=output_hash,
            runtime_id=self.runtime_id,
            verifier_id=self.verifier_id,
            evidence_id=evidence_id,
            parent_execution_id=(
                self.delegation.parent_execution_id if self.delegation else None
            ),
        )
