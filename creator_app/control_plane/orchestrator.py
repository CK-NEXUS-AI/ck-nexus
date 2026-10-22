"""Thin orchestration seam over existing CK-NEXUS agent capabilities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from creator_app.ai_team.intelligence.parallel_executor import ParallelExecutor, TaskStatus
from creator_app.ai_team.team_director import TeamDirector
from creator_app.dev_assistants.orchestrator import DevAssistantFabric

from .models import ControlPlaneRequest, ExecutionState, TaskGraph, TaskNode

NodeHandler = Callable[[TaskNode], Awaitable[Any] | Any]


@dataclass(frozen=True, slots=True)
class DispatchResult:
    execution_state: ExecutionState
    results: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class _RoleSpec:
    role: str
    capabilities: tuple[str, ...]


_ROLE_SPECS = (
    _RoleSpec("research", ("repo_analysis", "web")),
    _RoleSpec("implementation", ("code_edit",)),
    _RoleSpec("verification", ("test_fix",)),
    _RoleSpec("security", ("sandbox",)),
)


class ControlPlaneOrchestrator:
    """Build deterministic, bounded task graphs without executing workers."""

    def __init__(
        self,
        fabric: DevAssistantFabric | None = None,
        team_director: TeamDirector | None = None,
    ) -> None:
        self.fabric = fabric or DevAssistantFabric()
        self.team_director = team_director or TeamDirector()

    def plan(
        self,
        description: str,
        *,
        priority: int = 2,
        context: str = "",
    ) -> TaskGraph:
        request = ControlPlaneRequest(description=description, priority=priority, context=context)
        nodes: list[TaskNode] = []
        previous_id: str | None = None
        for index, spec in enumerate(_ROLE_SPECS, start=1):
            node_id = f"task-{index:02d}-{spec.role}"
            candidates = self.fabric.select(spec.capabilities, limit=3, require_installed=True)
            nodes.append(
                TaskNode(
                    node_id=node_id,
                    role=spec.role,
                    task=self._task_for(spec.role, request.description),
                    required_capabilities=spec.capabilities,
                    depends_on=(previous_id,) if previous_id and spec.role != "security" else (),
                    candidates=tuple(row["assistant_id"] for row in candidates),
                )
            )
            if spec.role in {"research", "implementation"}:
                previous_id = node_id
        implementation_id = next(node.node_id for node in nodes if node.role == "implementation")
        nodes = [
            node
            if node.role not in {"verification", "security"}
            else TaskNode(
                node_id=node.node_id,
                role=node.role,
                task=node.task,
                required_capabilities=node.required_capabilities,
                depends_on=(implementation_id,),
                candidates=node.candidates,
                state=node.state,
            )
            for node in nodes
        ]
        return TaskGraph(request=request, nodes=tuple(nodes))

    @staticmethod
    def queue_payloads(graph: TaskGraph) -> list[dict[str, Any]]:
        """Adapt planned graph nodes to queue-safe worker payloads only."""
        return [graph.as_queue_payload(node.node_id) for node in graph.nodes]

    def default_handlers(self) -> dict[str, NodeHandler]:
        """Route each graph role through the existing TeamDirector by default."""

        def handle(node: TaskNode) -> Any:
            result = self.team_director.process_request(
                node.task,
                priority=2,
                context=f"CK-NEXUS control-plane role={node.role}; planned node={node.node_id}",
            )
            return {
                "final_output": result.final_output,
                "status": result.status.value,
                "team_members_used": list(result.team_members_used),
                "confidence": result.confidence,
            }

        return {spec.role: handle for spec in _ROLE_SPECS}

    async def dispatch(
        self,
        graph: TaskGraph,
        *,
        handlers: dict[str, NodeHandler] | None = None,
        parallel_executor: ParallelExecutor | None = None,
        timeout: float = 30.0,
    ) -> DispatchResult:
        """Dispatch ready nodes in bounded waves; never bypass graph dependencies."""
        executor = parallel_executor or ParallelExecutor(max_concurrency=3)
        active_handlers = handlers or self.default_handlers()
        results: dict[str, dict[str, Any]] = {}
        pending = {node.node_id: node for node in graph.nodes}

        while pending:
            ready: list[TaskNode] = []
            for node in pending.values():
                if all(results.get(dep, {}).get("state") == "completed" for dep in node.depends_on):
                    ready.append(node)
                elif any(
                    results.get(dep, {}).get("state") in {"failed", "blocked_dependency"}
                    for dep in node.depends_on
                ):
                    results[node.node_id] = {"state": "blocked_dependency"}

            for node_id in list(results):
                pending.pop(node_id, None)
            if not ready:
                if pending:
                    for node in pending.values():
                        results[node.node_id] = {"state": "blocked_dependency"}
                    pending.clear()
                break

            tasks = []
            for node in ready:
                handler = active_handlers.get(node.role)
                if handler is None:

                    async def missing_handler(n: TaskNode = node) -> Any:
                        raise RuntimeError(f"no handler registered for role: {n.role}")

                    tasks.append((node.node_id, missing_handler))
                else:

                    async def invoke(h: NodeHandler = handler, n: TaskNode = node) -> Any:
                        value = h(n)
                        if hasattr(value, "__await__"):
                            return await value
                        return value

                    tasks.append((node.node_id, invoke))

            batch = await executor.run_batch(
                f"control-plane-{graph.request.description[:32]}",
                tasks,
                timeout=timeout,
            )
            for item in batch:
                results[item.task_id] = {
                    "state": "completed" if item.status is TaskStatus.COMPLETED else "failed",
                    "result": item.result,
                    "error": item.error,
                }
            for node in ready:
                pending.pop(node.node_id, None)

        all_completed = bool(graph.nodes) and len(results) == len(graph.nodes) and all(
            item.get("state") == "completed" for item in results.values()
        )
        return DispatchResult(
            execution_state=ExecutionState.COMPLETED if all_completed else ExecutionState.FAILED,
            results=results,
        )

    @staticmethod
    def _task_for(role: str, description: str) -> str:
        prompts = {
            "research": f"Research and clarify constraints for: {description}",
            "implementation": f"Prepare the smallest implementation for: {description}",
            "verification": f"Verify the proposed implementation for: {description}",
            "security": f"Review security and policy implications for: {description}",
        }
        return prompts[role]
