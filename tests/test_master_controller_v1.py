from creator_app.master_controller import (
    MasterController,
    RiskLevel,
    ToolLane,
)


def test_run_command_selects_operational_precheck_lanes() -> None:
    plan = MasterController().plan("CK-NEXUS RUN")

    assert plan.risk == RiskLevel.READ_ONLY
    assert plan.lanes == (
        ToolLane.GITHUB,
        ToolLane.VPS_DOCKER,
        ToolLane.GMAIL,
        ToolLane.AGNES,
        ToolLane.EVIDENCE,
    )
    assert plan.auto_execute_allowed is True
    assert plan.production_effect is False


def test_content_research_routes_to_files_web_agnes_and_evidence() -> None:
    plan = MasterController().plan(
        "สกัดเนื้อหา Pinterest แล้ววิจัยและพัฒนา CK-NEXUS"
    )

    assert ToolLane.FILE_CONTENT in plan.lanes
    assert ToolLane.WEB_RESEARCH in plan.lanes
    assert ToolLane.AGNES in plan.lanes
    assert ToolLane.EVIDENCE in plan.lanes
    assert plan.risk == RiskLevel.REVERSIBLE_DEV


def test_q10_routes_to_vps_and_evidence() -> None:
    plan = MasterController().plan("ตรวจสอบ Q10 Codex Security บน VPS")

    assert ToolLane.VPS_DOCKER in plan.lanes
    assert ToolLane.EVIDENCE in plan.lanes
    assert plan.production_effect is False


def test_unavailable_lane_blocks_automatic_execution() -> None:
    plan = MasterController().plan(
        "ตรวจ Q10 บน VPS",
        available_lanes={"vps_docker": False},
    )

    assert plan.auto_execute_allowed is False
    assert "lane_unavailable:vps_docker" in plan.blockers


def test_external_send_requires_human_gate() -> None:
    plan = MasterController().plan("ส่งอีเมลตอบกลับ Reconix")

    assert plan.risk == RiskLevel.EXTERNAL_WRITE
    assert plan.auto_execute_allowed is False
    assert any(step.human_approval_required for step in plan.steps)


def test_production_action_never_auto_executes() -> None:
    plan = MasterController().plan("merge แล้ว deploy production")

    assert plan.risk == RiskLevel.PRODUCTION
    assert plan.auto_execute_allowed is False
    assert plan.production_effect is False
    assert plan.steps[-1].human_approval_required is True


def test_empty_command_fails_closed() -> None:
    try:
        MasterController().plan("   ")
    except ValueError as exc:
        assert "command is required" in str(exc)
    else:
        raise AssertionError("empty command must fail closed")
