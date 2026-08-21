from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class EvidenceNode(BaseModel):
    evidence_id: str
    kind: str
    subject: str
    payload_digest: str
    parents: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceGraph:
    """Append-only in-memory evidence DAG for development evidence."""

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}

    @staticmethod
    def digest_payload(payload: object) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def append(
        self,
        *,
        evidence_id: str,
        kind: str,
        subject: str,
        payload: object,
        parents: list[str] | None = None,
    ) -> EvidenceNode:
        if evidence_id in self._nodes:
            raise ValueError("evidence_id already exists")
        parent_ids = list(parents or [])
        unknown = [parent for parent in parent_ids if parent not in self._nodes]
        if unknown:
            raise ValueError(f"unknown parent evidence: {unknown}")
        node = EvidenceNode(
            evidence_id=evidence_id,
            kind=kind,
            subject=subject,
            payload_digest=self.digest_payload(payload),
            parents=parent_ids,
        )
        self._nodes[evidence_id] = node
        return node

    def get(self, evidence_id: str) -> EvidenceNode:
        return self._nodes[evidence_id]

    def lineage(self, evidence_id: str) -> list[EvidenceNode]:
        ordered: list[EvidenceNode] = []
        seen: set[str] = set()

        def visit(current: str) -> None:
            if current in seen:
                return
            seen.add(current)
            node = self.get(current)
            for parent in node.parents:
                visit(parent)
            ordered.append(node)

        visit(evidence_id)
        return ordered
