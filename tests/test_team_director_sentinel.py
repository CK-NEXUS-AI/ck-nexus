from creator_app.ai_team.agent_models import TaskResult, TaskStatus, TeamPlan
from creator_app.ai_team.team_director import TeamDirector


def test_team_director_routes_explicit_artifact_requests_to_sentinel() -> None:
    team = TeamDirector()
    result = team.process_request("inspect artifact", evidence_bundle={"subject_sha": "bad"})

    assert result.status is TaskStatus.BLOCKED
    assert "Sentinel" in result.team_members_used
    assert result.step_results[0].metadata["evidence_status"] == "INCOMPLETE"
    assert result.plan.estimated_duration == result.steps_total * 10.0


def test_team_director_routes_artifact_requests_to_sentinel_without_bundle() -> None:
    result = TeamDirector().process_request("inspect artifact")

    assert result.status is TaskStatus.BLOCKED
    assert "Sentinel" in result.team_members_used
    assert result.step_results[0].metadata["evidence_status"] == "MISSING"


def test_team_director_routes_production_verification_to_sentinel() -> None:
    result = TeamDirector().process_request("verify production deployment")

    assert result.status is TaskStatus.BLOCKED
    assert "Sentinel" in result.team_members_used
    assert result.step_results[0].metadata["evidence_status"] == "MISSING"
    assert result.plan.estimated_duration == result.steps_total * 10.0


def test_team_director_does_not_route_ordinary_verification_to_sentinel() -> None:
    result = TeamDirector().process_request("improve MCP routing")

    assert result.status is TaskStatus.COMPLETED
    assert "Sentinel" not in result.team_members_used


def test_team_director_blocks_empty_plan() -> None:
    team = TeamDirector()

    class EmptyPlanDirector(type(team.director)):
        def process(self, request, context=None):
            return TaskResult(
                task_id="empty-plan",
                agent_name="Director",
                agent_role="director",
                status=TaskStatus.COMPLETED,
                output="empty",
                metadata={"plan": TeamPlan(request_id=request.request_id)},
            )

    team.director = EmptyPlanDirector()
    result = team.process_request("unmatched request")

    assert result.status is TaskStatus.BLOCKED
    assert result.steps_total == 0
    assert result.steps_completed == 0
