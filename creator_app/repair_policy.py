from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PolicyViolation(RuntimeError):
    pass


class RepairPhase(StrEnum):
    DETECTED = "detected"
    RECOVERING = "recovering"
    REPAIRING = "repairing"
    VALIDATING = "validating"
    CANARY = "canary"
    READY_TO_PROMOTE = "ready_to_promote"
    PROMOTED = "promoted"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ESCALATED = "escalated"


@dataclass(frozen=True, slots=True)
class RepairPolicy:
    """Safety policy for automation; it intentionally has no privileged executor."""

    max_recovery_attempts: int = 3
    max_code_repair_attempts: int = 2
    require_isolated_code_repair: bool = True
    require_canary: bool = True
    require_rollback_target: bool = True
    allow_direct_production_mutation: bool = False
    allow_privileged_operations: bool = False

    def __post_init__(self) -> None:
        if self.max_recovery_attempts < 1 or self.max_code_repair_attempts < 1:
            raise ValueError("repair attempt limits must be at least one")
        if not self.require_isolated_code_repair:
            raise ValueError("isolated code repair is mandatory")
        if not self.require_canary:
            raise ValueError("canary validation is mandatory")
        if not self.require_rollback_target:
            raise ValueError("rollback target is mandatory")
        if self.allow_direct_production_mutation:
            raise ValueError("direct production mutation is forbidden")
        if self.allow_privileged_operations:
            raise ValueError("privileged repair operations are forbidden")


@dataclass(slots=True)
class RepairSession:
    incident_id: str
    policy: RepairPolicy = field(default_factory=RepairPolicy)
    phase: RepairPhase = RepairPhase.DETECTED
    recovery_attempts: int = 0
    code_repair_attempts: int = 0
    deterministic_recovery_exhausted: bool = False
    isolated_workspace: bool = False
    tests_passed: bool = False
    security_checks_passed: bool = False
    immutable_candidate: str | None = None
    rollback_target: str | None = None
    canary_passed: bool = False

    def __post_init__(self) -> None:
        if not self.incident_id.strip():
            raise ValueError("incident_id must not be empty")

    def begin_deterministic_recovery(self) -> int:
        """Try safe recovery before any AI/code repair is permitted."""
        if self.deterministic_recovery_exhausted:
            raise PolicyViolation("deterministic recovery is already exhausted")
        if self.phase is not RepairPhase.DETECTED:
            raise PolicyViolation("deterministic recovery can only start from detected state")
        if self.recovery_attempts >= self.policy.max_recovery_attempts:
            self.deterministic_recovery_exhausted = True
            self.phase = RepairPhase.ESCALATED
            raise PolicyViolation("deterministic recovery attempt limit reached")
        self.recovery_attempts += 1
        self.phase = RepairPhase.RECOVERING
        return self.recovery_attempts

    def finish_deterministic_recovery(self, *, recovered: bool) -> None:
        if self.phase is not RepairPhase.RECOVERING:
            raise PolicyViolation("no deterministic recovery attempt is active")
        if recovered:
            self.phase = RepairPhase.PROMOTED
            return
        if self.recovery_attempts >= self.policy.max_recovery_attempts:
            self.deterministic_recovery_exhausted = True
            self.phase = RepairPhase.ESCALATED
        else:
            self.phase = RepairPhase.DETECTED

    def begin_code_repair(
        self,
        *,
        isolated_workspace: bool,
        direct_production_mutation: bool = False,
        requests_privileged_access: bool = False,
    ) -> int:
        if direct_production_mutation:
            raise PolicyViolation("direct production mutation is forbidden")
        if requests_privileged_access:
            raise PolicyViolation(
                "root, privileged operations, and Docker socket access are forbidden"
            )
        if not self.deterministic_recovery_exhausted:
            raise PolicyViolation("deterministic recovery must be exhausted before code repair")
        if self.phase not in {RepairPhase.ESCALATED, RepairPhase.ROLLED_BACK}:
            raise PolicyViolation("code repair is not valid in the current state")
        if self.policy.require_isolated_code_repair and not isolated_workspace:
            raise PolicyViolation("code repair requires an isolated workspace")
        if self.code_repair_attempts >= self.policy.max_code_repair_attempts:
            self.phase = RepairPhase.ESCALATED
            raise PolicyViolation("code repair attempt limit reached")

        self.code_repair_attempts += 1
        self.isolated_workspace = isolated_workspace
        self.tests_passed = False
        self.security_checks_passed = False
        self.immutable_candidate = None
        self.canary_passed = False
        self.phase = RepairPhase.REPAIRING
        return self.code_repair_attempts

    def submit_candidate(
        self,
        *,
        candidate_id: str,
        rollback_target: str,
        tests_passed: bool,
        security_checks_passed: bool,
    ) -> None:
        if self.phase is not RepairPhase.REPAIRING:
            raise PolicyViolation("candidate can only be submitted from code repair")
        if not candidate_id.strip():
            raise PolicyViolation("an immutable candidate identifier is required")
        if self.policy.require_rollback_target and not rollback_target.strip():
            raise PolicyViolation("a rollback target is required before canary")

        self.tests_passed = tests_passed
        self.security_checks_passed = security_checks_passed
        if not tests_passed or not security_checks_passed:
            self.phase = RepairPhase.ESCALATED
            raise PolicyViolation("tests and security checks must pass before canary")

        self.immutable_candidate = candidate_id
        self.rollback_target = rollback_target
        self.phase = RepairPhase.VALIDATING

    def begin_canary(self) -> None:
        if self.phase is not RepairPhase.VALIDATING:
            raise PolicyViolation("validated candidate is required before canary")
        if not self.immutable_candidate or not self.rollback_target:
            raise PolicyViolation("candidate and rollback target are required")
        self.phase = RepairPhase.CANARY

    def finish_canary(self, *, passed: bool) -> None:
        if self.phase is not RepairPhase.CANARY:
            raise PolicyViolation("no canary is active")
        self.canary_passed = passed
        self.phase = RepairPhase.READY_TO_PROMOTE if passed else RepairPhase.ROLLING_BACK

    def promote(self) -> None:
        if self.policy.require_canary and (
            self.phase is not RepairPhase.READY_TO_PROMOTE or not self.canary_passed
        ):
            raise PolicyViolation("a passing canary is required before promotion")
        if not self.rollback_target:
            raise PolicyViolation("rollback target is required before promotion")
        self.phase = RepairPhase.PROMOTED

    def rollback(self) -> str:
        if self.phase not in {RepairPhase.ROLLING_BACK, RepairPhase.READY_TO_PROMOTE}:
            raise PolicyViolation("rollback is only valid after canary")
        if not self.rollback_target:
            raise PolicyViolation("rollback target is missing")
        self.phase = RepairPhase.ROLLED_BACK
        return self.rollback_target
