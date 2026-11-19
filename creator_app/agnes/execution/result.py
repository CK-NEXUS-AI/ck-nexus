from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ExecutionStatus(StrEnum):
    REQUESTED = "requested"
    VALIDATED = "validated"
    POLICY_ALLOWED = "policy_allowed"
    WAITING_APPROVAL = "waiting_approval"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class SkillExecutionResult:
    execution_id: str
    skill_id: str
    status: ExecutionStatus
    output: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    policy_decision: str = "allow"
    manifest_hash: str | None = None
    approval_fingerprint: str | None = None
    risk_class: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "skill_id": self.skill_id,
            "status": self.status.value,
            "output": self.output,
            "evidence_refs": self.evidence_refs,
            "artifacts": self.artifacts,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "policy_decision": self.policy_decision,
            "manifest_hash": self.manifest_hash,
            "approval_fingerprint": self.approval_fingerprint,
            "risk_class": self.risk_class,
        }
