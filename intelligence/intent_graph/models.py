from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntentKind(str, Enum):
    QUERY = "query"
    RESEARCH = "research"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"


@dataclass(frozen=True)
class IntentNode:
    node_id: str
    kind: IntentKind
    goal: str
    confidence: float
    dependencies: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class IntentGraph:
    nodes: dict[str, IntentNode] = field(default_factory=dict)

    def add(self, node: IntentNode) -> None:
        if not 0.0 <= node.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        self.nodes[node.node_id] = node

    def roots(self) -> list[IntentNode]:
        return [node for node in self.nodes.values() if not node.dependencies]
