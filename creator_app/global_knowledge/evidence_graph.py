"""Citation graph and evidence-lineage structures for CK-NEXUS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceNodeKind(StrEnum):
    SOURCE = "source"
    CLAIM = "claim"


class EvidenceEdgeKind(StrEnum):
    CITES = "cites"
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


@dataclass(frozen=True, slots=True)
class EvidenceGraphNode:
    node_id: str
    kind: EvidenceNodeKind
    observed_at: str
    source_id: str | None = None
    claim_id: str | None = None

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if self.kind is EvidenceNodeKind.SOURCE and not self.source_id:
            raise ValueError("source nodes require source_id")
        if self.kind is EvidenceNodeKind.CLAIM and not self.claim_id:
            raise ValueError("claim nodes require claim_id")


@dataclass(frozen=True, slots=True)
class EvidenceGraphEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    kind: EvidenceEdgeKind
    independent_validation: bool = False

    def __post_init__(self) -> None:
        if not self.edge_id.strip():
            raise ValueError("edge_id is required")
        if self.from_node_id == self.to_node_id:
            raise ValueError("self edges are not allowed")


@dataclass(frozen=True, slots=True)
class LineagePath:
    start_node_id: str
    root_node_id: str
    node_ids: tuple[str, ...]
    depth: int
    independent_validation_edges: int
    cycle_detected: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceGraphReport:
    node_count: int
    edge_count: int
    citation_cycles: tuple[tuple[str, ...], ...]


class EvidenceGraph:
    def __init__(
        self,
        nodes: tuple[EvidenceGraphNode, ...],
        edges: tuple[EvidenceGraphEdge, ...],
    ) -> None:
        node_map = {node.node_id: node for node in nodes}
        if len(node_map) != len(nodes):
            raise ValueError("node_id values must be unique")

        edge_ids = {edge.edge_id for edge in edges}
        if len(edge_ids) != len(edges):
            raise ValueError("edge_id values must be unique")

        missing = sorted(
            {
                endpoint
                for edge in edges
                for endpoint in (edge.from_node_id, edge.to_node_id)
                if endpoint not in node_map
            }
        )
        if missing:
            raise ValueError("edge references missing nodes: " + ",".join(missing))

        self.nodes = nodes
        self.edges = edges
        self._node_map = node_map

    def report(self) -> EvidenceGraphReport:
        return EvidenceGraphReport(
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            citation_cycles=self._detect_citation_cycles(),
        )

    def trace_lineage(self, start_node_id: str) -> tuple[LineagePath, ...]:
        if start_node_id not in self._node_map:
            raise KeyError(start_node_id)

        parent_edges: dict[str, list[EvidenceGraphEdge]] = {}
        for edge in self.edges:
            if edge.kind in {EvidenceEdgeKind.CITES, EvidenceEdgeKind.DERIVED_FROM}:
                parent_edges.setdefault(edge.from_node_id, []).append(edge)

        paths: list[LineagePath] = []

        def walk(
            current: str,
            path: tuple[str, ...],
            validation_count: int,
        ) -> None:
            if current in path:
                cycle_path = path + (current,)
                paths.append(
                    LineagePath(
                        start_node_id=start_node_id,
                        root_node_id=current,
                        node_ids=cycle_path,
                        depth=max(0, len(cycle_path) - 1),
                        independent_validation_edges=validation_count,
                        cycle_detected=True,
                    )
                )
                return

            parents = parent_edges.get(current, [])
            next_path = path + (current,)
            if not parents:
                paths.append(
                    LineagePath(
                        start_node_id=start_node_id,
                        root_node_id=current,
                        node_ids=next_path,
                        depth=max(0, len(next_path) - 1),
                        independent_validation_edges=validation_count,
                    )
                )
                return

            for edge in parents:
                walk(
                    edge.to_node_id,
                    next_path,
                    validation_count + int(edge.independent_validation),
                )

        walk(start_node_id, (), 0)
        return tuple(paths)

    def _detect_citation_cycles(self) -> tuple[tuple[str, ...], ...]:
        adjacency: dict[str, list[str]] = {}
        for edge in self.edges:
            if edge.kind is EvidenceEdgeKind.CITES:
                adjacency.setdefault(edge.from_node_id, []).append(edge.to_node_id)

        cycles: set[tuple[str, ...]] = set()
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                index = visiting.index(node_id)
                cycles.add(tuple(visiting[index:] + [node_id]))
                return
            if node_id in visited:
                return

            visiting.append(node_id)
            for target in adjacency.get(node_id, []):
                visit(target)
            visiting.pop()
            visited.add(node_id)

        for node_id in self._node_map:
            visit(node_id)

        return tuple(sorted(cycles))
