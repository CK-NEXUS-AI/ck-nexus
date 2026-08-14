from __future__ import annotations

import pytest

from intelligence.intent_graph.models import IntentGraph, IntentKind, IntentNode
from intelligence.task_dag.models import TaskDAG, TaskNode, TaskState
from services.cognitive_fabric.models import CognitiveRequest, ProviderCapabilities, ProviderResponse
from services.cognitive_fabric.router import CognitiveRouter
from services.cognitive_governor.governor import CognitiveGovernor


class FakeProvider:
    name = "fake"

    async def generate(self, request: CognitiveRequest) -> ProviderResponse:
        return ProviderResponse(provider=self.name, model="fake-1", content=request.prompt, latency_ms=1)

    async def stream(self, request: CognitiveRequest):
        yield request.prompt

    async def health(self) -> dict[str, object]:
        return {"status": "ok"}

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(tool_calling=True, structured_output=True)

    async def estimate_cost(self, request: CognitiveRequest) -> float:
        return 0.0


@pytest.mark.asyncio
async def test_router_and_governor_fail_closed_for_unknown_risk() -> None:
    request = CognitiveRequest("r1", "c1", "t1", "u1", "hello", metadata={"risk": "mystery"})
    governor = CognitiveGovernor()
    decision = await governor.evaluate(request)
    assert decision.allowed is False

    router = CognitiveRouter()
    router.register(FakeProvider())
    provider, route = await router.select(request)
    assert provider.name == "fake"
    assert route.provider == "fake"


def test_intent_graph_and_task_dag() -> None:
    graph = IntentGraph()
    graph.add(IntentNode("i1", IntentKind.PLAN, "plan work", 0.9))
    assert [node.node_id for node in graph.roots()] == ["i1"]

    dag = TaskDAG()
    dag.add(TaskNode("a", "research", state=TaskState.SUCCEEDED))
    dag.add(TaskNode("b", "execute", dependencies={"a"}))
    assert [task.task_id for task in dag.ready()] == ["b"]
