"""Bounded task-graph contracts for the CK-NEXUS control plane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExecutionState(StrEnum):
    PLANNED_NOT_EXECUTED = "PLANNED_NOT_EXECUTED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ControlPlaneRequest:
    description: str
    priority: int = 2
    context: str = ""
    evidence_bundle: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("request must not be empty")
        if not 0 <= self.priority <= 3:
            raise ValueError("priority must be between 0 and 3")


@dataclass(frozen=True, slots=True)
class TaskNode:
    node_id: str
    role: str
    task: str
    required_capabilities: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    candidates: tuple[str, ...] = ()
    state: ExecutionState = ExecutionState.PLANNED_NOT_EXECUTED
    evidence_bundle: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TaskGraph:
    request: ControlPlaneRequest
    nodes: tuple[TaskNode, ...]
    execution_state: ExecutionState = ExecutionState.PLANNED_NOT_EXECUTED
    production_status: str = "NO-GO"
    external_mutation_authorized: bool = False
    release_evidence: bool = False

    def as_queue_payload(self, node_id: str) -> dict[str, Any]:
        """Serialize one planned node into a queue-safe, non-production payload."""
        node = next((item for item in self.nodes if item.node_id == node_id), None)
        if node is None:
            raise ValueError(f"unknown task node: {node_id}")
        return {
            "handler": node.role,
            "node_id": node.node_id,
            "task": node.task,
            "required_capabilities": list(node.required_capabilities),
            "depends_on": list(node.depends_on),
            "candidates": list(node.candidates),
            "production_status": "NO-GO",
            "external_mutation_authorized": False,
            "release_evidence": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": {
                "description": self.request.description,
                "priority": self.request.priority,
                "context": self.request.context,
            },
            "execution_state": self.execution_state.value,
            "production_status": self.production_status,
            "external_mutation_authorized": self.external_mutation_authorized,
            "release_evidence": self.release_evidence,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "role": node.role,
                    "task": node.task,
                    "required_capabilities": list(node.required_capabilities),
                    "depends_on": list(node.depends_on),
                    "candidates": list(node.candidates),
                    "state": node.state.value,
                }
                for node in self.nodes
            ],
        }
