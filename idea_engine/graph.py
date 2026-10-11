from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .models import EdgeType, IdeaEdge, IdeaNode

_TOKEN = re.compile(r"[A-Za-z0-9ก-๙_+-]+")


def _normalize_token(token: str) -> str:
    value = token.lower()
    # Tiny deterministic normalizer for common English inflections; this is not
    # a semantic model and intentionally stays dependency-free.
    if len(value) > 6 and value.endswith("ing"):
        value = value[:-3]
    elif len(value) > 5 and value.endswith("er"):
        value = value[:-2]
    elif len(value) > 4 and value.endswith("s"):
        value = value[:-1]
    return value


def text_similarity(left: str, right: str) -> float:
    a = {_normalize_token(token) for token in _TOKEN.findall(left)}
    b = {_normalize_token(token) for token in _TOKEN.findall(right)}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True, slots=True)
class SimilarNode:
    node: IdeaNode
    score: float


class IdeaGraph:
    def __init__(self, storage_path: str | Path) -> None:
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.nodes: dict[str, IdeaNode] = {}
        self.edges: dict[str, IdeaEdge] = {}
        self.history: list[dict[str, object]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.nodes = {item["id"]: IdeaNode(**item) for item in raw.get("nodes", [])}
        self.edges = {item["edge_id"]: IdeaEdge(**item) for item in raw.get("edges", [])}
        self.history = list(raw.get("history", []))

    def _save(self) -> None:
        payload = {
            "nodes": [node.as_dict() for node in self.nodes.values()],
            "edges": [edge.as_dict() for edge in self.edges.values()],
            "history": self.history,
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_node(self, node: IdeaNode, *, actor: str = "idea-engine") -> IdeaNode:
        if node.id in self.nodes:
            raise ValueError("node id already exists")
        self.nodes[node.id] = node
        self.history.append({"action": "node_created", "node_id": node.id, "actor": actor})
        self._save()
        return node

    def get_node(self, node_id: str) -> IdeaNode | None:
        return self.nodes.get(node_id)

    def update_node(
        self, node_id: str, *, actor: str = "idea-engine", **changes: object
    ) -> IdeaNode:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(node_id)
        allowed = {
            "title",
            "summary",
            "status",
            "tags",
            "source_refs",
            "confidence",
            "raw_input",
            "lens_notes",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError("unsupported node fields: " + ", ".join(sorted(unknown)))
        before = node.as_dict()
        for key, value in changes.items():
            setattr(node, key, value)
        from datetime import UTC, datetime

        node.updated_at = datetime.now(UTC).isoformat()
        self.history.append(
            {
                "action": "node_updated",
                "node_id": node_id,
                "actor": actor,
                "changed_fields": sorted(changes),
                "before": before,
            }
        )
        self._save()
        return node

    def archive_node(self, node_id: str, *, actor: str = "idea-engine") -> IdeaNode:
        return self.update_node(node_id, actor=actor, status="archived")

    def add_edge(self, edge: IdeaEdge, *, actor: str = "idea-engine") -> IdeaEdge:
        if edge.from_node_id not in self.nodes or edge.to_node_id not in self.nodes:
            raise KeyError("edge endpoints must exist")
        if edge.type not in {item.value for item in EdgeType}:
            raise ValueError("unknown edge type")
        if not 0 <= edge.weight <= 1:
            raise ValueError("edge weight must be 0..1")
        self.edges[edge.edge_id] = edge
        self.history.append({"action": "edge_created", "edge_id": edge.edge_id, "actor": actor})
        self._save()
        return edge

    def similar(self, title: str, summary: str, *, limit: int = 5) -> tuple[SimilarNode, ...]:
        query = f"{title} {summary}".strip()
        ranked = [
            SimilarNode(node, text_similarity(query, f"{node.title} {node.summary}"))
            for node in self.nodes.values()
        ]
        ranked = [item for item in ranked if item.score > 0]
        ranked.sort(key=lambda item: (-item.score, item.node.id))
        return tuple(ranked[:limit])

    def link_similar(
        self,
        node: IdeaNode,
        *,
        threshold: float = 0.55,
        actor: str = "idea-engine",
    ) -> tuple[IdeaEdge, ...]:
        links: list[IdeaEdge] = []
        for item in self.similar(node.title, node.summary):
            if item.node.id == node.id or item.score < threshold:
                continue
            edge_type = EdgeType.EXTENDS if item.score >= 0.75 else EdgeType.ALTERNATIVE_TO
            edge = IdeaEdge(
                edge_id=str(uuid.uuid4()),
                from_node_id=node.id,
                to_node_id=item.node.id,
                type=edge_type.value,
                weight=round(item.score, 4),
                reason=(
                    "Similarity/dedup linker preserved both nodes "
                    "and linked their relationship."
                ),
                created_by=actor,
            )
            links.append(self.add_edge(edge, actor=actor))
        return tuple(links)

    def export_safe(self) -> dict[str, object]:
        # Graph model intentionally has no credential field.
        # Source refs are metadata identifiers only.
        return {
            "nodes": [node.as_dict() for node in self.nodes.values()],
            "edges": [edge.as_dict() for edge in self.edges.values()],
            "history": list(self.history),
        }
