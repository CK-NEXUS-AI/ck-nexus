import pytest

from creator_app.repair_policy import (
    PolicyViolation,
    RepairPhase,
    RepairPolicy,
    RepairSession,
)


def exhaust_deterministic_recovery(session: RepairSession) -> None:
    for _ in range(session.policy.max_recovery_attempts):
        session.begin_deterministic_recovery()
        session.finish_deterministic_recovery(recovered=False)


def test_code_repair_is_blocked_until_deterministic_recovery_is_exhausted() -> None:
    session = RepairSession("incident-1")
    with pytest.raises(PolicyViolation, match="deterministic recovery"):
        session.begin_code_repair(isolated_workspace=True)


def test_recovery_attempts_are_bounded() -> None:
    session = RepairSession("incident-2", policy=RepairPolicy(max_recovery_attempts=2))
    exhaust_deterministic_recovery(session)
    assert session.recovery_attempts == 2
    assert session.deterministic_recovery_exhausted is True
    assert session.phase is RepairPhase.ESCALATED
    with pytest.raises(PolicyViolation, match="already exhausted"):
        session.begin_deterministic_recovery()


def test_direct_mutation_privileged_access_and_nonisolated_repair_are_forbidden() -> None:
    session = RepairSession("incident-3")
    exhaust_deterministic_recovery(session)

    with pytest.raises(PolicyViolation, match="direct production"):
        session.begin_code_repair(isolated_workspace=True, direct_production_mutation=True)
    with pytest.raises(PolicyViolation, match="privileged"):
        session.begin_code_repair(isolated_workspace=True, requests_privileged_access=True)
    with pytest.raises(PolicyViolation, match="isolated workspace"):
        session.begin_code_repair(isolated_workspace=False)


def test_safe_code_repair_requires_validation_canary_and_rollback_target() -> None:
    session = RepairSession("incident-4")
    exhaust_deterministic_recovery(session)
    session.begin_code_repair(isolated_workspace=True)
    session.submit_candidate(
        candidate_id="sha256:candidate",
        rollback_target="sha256:last-known-good",
        tests_passed=True,
        security_checks_passed=True,
    )

    with pytest.raises(PolicyViolation, match="passing canary"):
        session.promote()

    session.begin_canary()
    session.finish_canary(passed=True)
    session.promote()
    assert session.phase is RepairPhase.PROMOTED


def test_failed_canary_routes_to_rollback() -> None:
    session = RepairSession("incident-5")
    exhaust_deterministic_recovery(session)
    session.begin_code_repair(isolated_workspace=True)
    session.submit_candidate(
        candidate_id="sha256:bad-candidate",
        rollback_target="sha256:known-good",
        tests_passed=True,
        security_checks_passed=True,
    )
    session.begin_canary()
    session.finish_canary(passed=False)
    assert session.phase is RepairPhase.ROLLING_BACK
    assert session.rollback() == "sha256:known-good"
    assert session.phase is RepairPhase.ROLLED_BACK


def test_failed_validation_never_reaches_canary() -> None:
    session = RepairSession("incident-6")
    exhaust_deterministic_recovery(session)
    session.begin_code_repair(isolated_workspace=True)
    with pytest.raises(PolicyViolation, match="tests and security"):
        session.submit_candidate(
            candidate_id="sha256:candidate",
            rollback_target="sha256:known-good",
            tests_passed=False,
            security_checks_passed=True,
        )
    assert session.phase is RepairPhase.ESCALATED


def test_unsafe_policy_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="isolated"):
        RepairPolicy(require_isolated_code_repair=False)
    with pytest.raises(ValueError, match="canary"):
        RepairPolicy(require_canary=False)
    with pytest.raises(ValueError, match="rollback"):
        RepairPolicy(require_rollback_target=False)
    with pytest.raises(ValueError, match="production mutation"):
        RepairPolicy(allow_direct_production_mutation=True)
    with pytest.raises(ValueError, match="privileged"):
        RepairPolicy(allow_privileged_operations=True)
