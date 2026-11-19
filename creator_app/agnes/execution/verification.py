from __future__ import annotations

from dataclasses import dataclass

from .manifest import ImmutableExecutionManifest
from .result import ExecutionStatus, SkillExecutionResult


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    valid: bool
    reason: str


class ResultVerifier:
    def verify(
        self,
        manifest: ImmutableExecutionManifest,
        result: SkillExecutionResult,
    ) -> VerificationDecision:
        if result.execution_id != manifest.execution_id:
            return VerificationDecision(False, "execution_id_mismatch")
        if result.skill_id != manifest.skill_id:
            return VerificationDecision(False, "skill_id_mismatch")
        if result.status not in {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.ROLLED_BACK,
        }:
            return VerificationDecision(False, "invalid_terminal_status")
        return VerificationDecision(True, "verified")
