from __future__ import annotations

import pytest

from creator_app.ai_team.ck_coordination import CKRole, WorkPacket, build_ck_v3_packet
from creator_app.ai_team.ck_v3_planner import CKV3Planner


def _packet() -> WorkPacket:
    return build_ck_v3_packet(
        task_id="CK3-PLAN-001",
        target="creator_app/device_bridge",
        objective="Prepare a read-only remote canary plan.",
        source_commit="a" * 40,
        allowed_actions=(
            "inspect remote contract",
            "define negative authentication tests",
            "prepare evidence-ready candidate report",
        ),
        expected_evidence=(
            "exact source commit",
            "test matrix",
            "risk notes",
        ),
    )


def test_compile_produces_non_authoritative_evidence_first_plan() -> None:
    plan = CKV3Planner.compile(_packet())

    assert plan.task_id == "CK3-PLAN-001"
    assert plan.source_commit == "a" * 40
    assert len(plan.steps) == 3
    assert plan.requires_independent_verification is True
    assert plan.execution_authority is False
    assert all(step.read_only_default for step in plan.steps)
    assert all(step.external_write is False for step in plan.steps)
    assert all(step.credential_access is False for step in plan.steps)
    assert all(step.production_mutation is False for step in plan.steps)
    assert all(step.evidence_required for step in plan.steps)


def test_compile_rejects_non_ck_v3_packet() -> None:
    packet = WorkPacket(
        task_id="CK2-PLAN-001",
        assignee=CKRole.CK_V2,
        target="repo:main",
        objective="verify",
        allowed_actions=("read source",),
        denied_actions=("production mutation",),
        expected_evidence=("exact source commit",),
        source_commit="a" * 40,
    )

    with pytest.raises(ValueError, match="ck_v3_packet_required"):
        CKV3Planner.compile(packet)


def test_compile_requires_exact_source_commit() -> None:
    packet = build_ck_v3_packet(
        task_id="CK3-PLAN-002",
        target="repo:main",
        objective="plan",
        source_commit="short",
        allowed_actions=("read source",),
        expected_evidence=("evidence",),
    )

    with pytest.raises(ValueError, match="exact_source_commit_required"):
        CKV3Planner.compile(packet)


@pytest.mark.parametrize(
    "action",
    [
        "deploy production now",
        "credential access for debugging",
        "export token to a report",
        "external write to remote service",
        "merge PR #14",
        "override policy for speed",
    ],
)
def test_compile_rejects_forbidden_action_text(action: str) -> None:
    packet = build_ck_v3_packet(
        task_id="CK3-PLAN-003",
        target="repo:main",
        objective="plan",
        source_commit="a" * 40,
        allowed_actions=(action,),
        expected_evidence=("evidence",),
    )

    with pytest.raises(ValueError, match="forbidden_action_in_allowed_set"):
        CKV3Planner.compile(packet)


def test_compile_normalizes_action_whitespace_and_step_ids() -> None:
    packet = build_ck_v3_packet(
        task_id="CK3-NORM",
        target="repo:main",
        objective="plan",
        source_commit="A" * 40,
        allowed_actions=("  inspect   source  ", "run   local tests"),
        expected_evidence=("run id",),
    )

    plan = CKV3Planner.compile(packet)

    assert plan.source_commit == "a" * 40
    assert [step.step_id for step in plan.steps] == ["CK3-NORM-S01", "CK3-NORM-S02"]
    assert [step.action for step in plan.steps] == ["inspect source", "run local tests"]
