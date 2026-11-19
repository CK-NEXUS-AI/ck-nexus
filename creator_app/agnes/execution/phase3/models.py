from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkspaceState(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING_PIPELINE = "running_pipeline"
    CANDIDATE = "candidate"
    DISCARDED = "discarded"
    ARCHIVED = "archived"


class PipelineState(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    WORKSPACE_CREATED = "workspace_created"
    BASELINE_CHECKED_OUT = "baseline_checked_out"
    CODE_PATCH_APPLIED = "code_patch_applied"
    TESTS_EXECUTED = "tests_executed"
    SECURITY_SCANNED = "security_scanned"
    DIFF_REVIEWED = "diff_reviewed"
    EVIDENCE_COLLECTED = "evidence_collected"
    CANDIDATE_READY = "candidate_ready"
    DISCARDED = "discarded"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PipelineHandle:
    pipeline_id: str
    execution_id: str


@dataclass(slots=True)
class PipelineStatus:
    pipeline_id: str
    execution_id: str
    correlation_id: str
    state: PipelineState
    workspace_id: str | None = None
    baseline_commit: str | None = None
    approval_fingerprint: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "state": self.state.value,
            "workspace_id": self.workspace_id,
            "baseline_commit": self.baseline_commit,
            "approval_fingerprint": self.approval_fingerprint,
            "history": list(self.history),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class CandidateArtifact:
    candidate_id: str
    execution_id: str
    pipeline_id: str
    baseline_commit: str
    result_commit: str | None
    diff: str
    test_result: dict[str, Any]
    security_scan: dict[str, Any]
    evidence_refs: tuple[str, ...]
    status: str
    created_at: str
    requires_merge_approval: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "execution_id": self.execution_id,
            "pipeline_id": self.pipeline_id,
            "baseline_commit": self.baseline_commit,
            "result_commit": self.result_commit,
            "diff": self.diff,
            "test_result": self.test_result,
            "security_scan": self.security_scan,
            "evidence_refs": list(self.evidence_refs),
            "status": self.status,
            "created_at": self.created_at,
            "requires_merge_approval": self.requires_merge_approval,
        }
