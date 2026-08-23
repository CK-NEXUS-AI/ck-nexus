from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json


@dataclass(frozen=True, slots=True)
class ProvenanceNode:
    node_id: str
    kind: str
    subject: str
    digest: str

    @classmethod
    def create(cls, *, kind: str, subject: str, payload: dict[str, object]) -> "ProvenanceNode":
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        node_id = hashlib.sha256(f"{kind}:{subject}:{digest}".encode()).hexdigest()
        return cls(node_id=node_id, kind=kind, subject=subject, digest=digest)


@dataclass(frozen=True, slots=True)
class ProvenanceEdge:
    source_id: str
    target_id: str
    relation: str


@dataclass(slots=True)
class ProvenanceGraph:
    nodes: dict[str, ProvenanceNode] = field(default_factory=dict)
    edges: list[ProvenanceEdge] = field(default_factory=list)

    def add_node(self, node: ProvenanceNode) -> None:
        self.nodes.setdefault(node.node_id, node)

    def link(self, source_id: str, target_id: str, relation: str) -> None:
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("provenance edge endpoints must exist")
        edge = ProvenanceEdge(source_id, target_id, relation)
        if edge not in self.edges:
            self.edges.append(edge)

    def predecessors(self, node_id: str) -> tuple[ProvenanceNode, ...]:
        source_ids = [edge.source_id for edge in self.edges if edge.target_id == node_id]
        return tuple(self.nodes[source_id] for source_id in source_ids)
