"""Deterministic DAG validation for CK-NEXUS task plans."""

from __future__ import annotations

from .contracts import PlanNode


class InvalidTaskGraph(ValueError):
    """Raised when a plan contains missing dependencies or a cycle."""


def validate_task_graph(nodes: tuple[PlanNode, ...]) -> tuple[str, ...]:
    """Validate dependencies and return a deterministic topological order."""
    by_id = {node.node_id: node for node in nodes}
    if len(by_id) != len(nodes):
        raise InvalidTaskGraph("duplicate node_id")
    for node in nodes:
        missing = [dependency for dependency in node.dependencies if dependency not in by_id]
        if missing:
            raise InvalidTaskGraph(f"missing dependencies for {node.node_id}: {missing}")

    indegree = {node.node_id: len(node.dependencies) for node in nodes}
    dependents: dict[str, list[str]] = {node.node_id: [] for node in nodes}
    for node in nodes:
        for dependency in node.dependencies:
            dependents[dependency].append(node.node_id)

    ready = sorted(node_id for node_id, count in indegree.items() if count == 0)
    ordered: list[str] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(node_id)
        for child in sorted(dependents[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()

    if len(ordered) != len(nodes):
        raise InvalidTaskGraph("task graph contains a cycle")
    return tuple(ordered)
