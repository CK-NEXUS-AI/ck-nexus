import asyncio
from types import SimpleNamespace

from creator_app.ai_team.intelligence.parallel_executor import ParallelExecutor
from creator_app.control_plane.models import ExecutionState
from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator


def test_dispatch_runs_ready_nodes_and_waits_for_dependencies() -> None:
    graph = ControlPlaneOrchestrator().plan("improve MCP routing")
    events: list[str] = []

    async def run() -> object:
        executor = ParallelExecutor(max_concurrency=2)
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda node: events.append(node.role) or "research-ok",
                "implementation": lambda node: events.append(node.role) or "implementation-ok",
                "verification": lambda node: events.append(node.role) or "verification-ok",
                "security": lambda node: events.append(node.role) or "security-ok",
            },
            parallel_executor=executor,
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.COMPLETED
    assert set(result.results) == {node.node_id for node in graph.nodes}
    assert events.index("implementation") < events.index("verification")
    assert events.index("implementation") < events.index("security")


def test_dispatch_stops_downstream_after_failed_dependency() -> None:
    graph = ControlPlaneOrchestrator().plan("repair API")

    async def run() -> object:
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda _node: "research-ok",
                "implementation": lambda _node: (_ for _ in ()).throw(RuntimeError("boom")),
                "verification": lambda _node: "should-not-run",
                "security": lambda _node: "should-not-run",
            },
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.FAILED
    assert result.results["task-02-implementation"]["state"] == "failed"
    assert result.results["task-03-verification"]["state"] == "blocked_dependency"
    assert result.results["task-04-security"]["state"] == "blocked_dependency"


def test_default_handlers_delegate_to_existing_team_director() -> None:
    class FakeTeam:
        def process_request(self, description: str, *, priority: int, context: str):
            return SimpleNamespace(
                final_output=f"handled:{description}",
                status=SimpleNamespace(value="completed"),
                team_members_used=("engineer",),
                confidence=0.9,
            )

    orchestrator = ControlPlaneOrchestrator(team_director=FakeTeam())
    handler = orchestrator.default_handlers()["implementation"]
    result = handler(orchestrator.plan("build feature").nodes[1])
    assert result["final_output"].startswith("handled:")
    assert result["team_members_used"] == ["engineer"]


def test_dispatch_fails_closed_for_cyclic_or_empty_graphs() -> None:
    from creator_app.control_plane.models import ControlPlaneRequest, TaskGraph, TaskNode

    orchestrator = ControlPlaneOrchestrator()
    cyclic = TaskGraph(
        request=ControlPlaneRequest(description="cycle test"),
        nodes=(
            TaskNode(node_id="a", role="research", task="a", depends_on=("b",)),
            TaskNode(node_id="b", role="implementation", task="b", depends_on=("a",)),
        ),
    )
    empty = TaskGraph(request=ControlPlaneRequest(description="empty test"), nodes=())

    async def run() -> tuple[object, object]:
        return await orchestrator.dispatch(cyclic, handlers={}), await orchestrator.dispatch(empty)

    cycle_result, empty_result = asyncio.run(run())
    assert cycle_result.execution_state is ExecutionState.FAILED
    assert all(item["state"] == "blocked_dependency" for item in cycle_result.results.values())
    assert empty_result.execution_state is ExecutionState.FAILED
    assert empty_result.results == {}


def test_plan_can_be_adapted_to_queue_payload_without_production_authority() -> None:
    graph = ControlPlaneOrchestrator().plan("queue safe worker")
    payload = graph.as_queue_payload("task-02-implementation")
    assert payload["handler"] == "implementation"
    assert payload["node_id"] == "task-02-implementation"
    assert payload["depends_on"] == ["task-01-research"]
    assert payload["production_status"] == "NO-GO"
    assert payload["external_mutation_authorized"] is False
    assert payload["release_evidence"] is False


def test_queue_adapter_rejects_unknown_node() -> None:
    graph = ControlPlaneOrchestrator().plan("queue safe worker")
    try:
        graph.as_queue_payload("missing-node")
    except ValueError as exc:
        assert "unknown task node" in str(exc)
    else:
        raise AssertionError("unknown node must be rejected")
