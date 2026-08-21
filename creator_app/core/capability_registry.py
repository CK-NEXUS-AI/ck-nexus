from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, Field


class CapabilityStatus(StrEnum):
    FOUND = "found"
    PARTIAL = "partial"
    EXPERIMENTAL = "experimental"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class Capability(BaseModel):
    capability_id: str
    name: str
    description: str
    category: str
    status: CapabilityStatus = CapabilityStatus.EXPERIMENTAL
    cost_weight: float = Field(default=1.0, ge=0.0)
    latency_ms: int = Field(default=0, ge=0)
    source_ref: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    exact_subject: str | None = None


class CapabilityRegistry:
    """In-memory registry with fail-closed verification promotion."""

    def __init__(self, capabilities: Iterable[Capability] | None = None) -> None:
        self._items: dict[str, Capability] = {}
        for capability in capabilities or ():
            self.register(capability)

    def register(self, capability: Capability) -> None:
        if (
            capability.status == CapabilityStatus.VERIFIED
            and (not capability.evidence_ids or not capability.exact_subject)
        ):
            raise ValueError("VERIFIED capability requires evidence_ids and exact_subject")
        self._items[capability.capability_id] = capability

    def get(self, capability_id: str) -> Capability | None:
        return self._items.get(capability_id)

    def find(
        self,
        *,
        category: str | None = None,
        status: CapabilityStatus | None = None,
    ) -> list[Capability]:
        items = list(self._items.values())
        if category is not None:
            items = [item for item in items if item.category == category]
        if status is not None:
            items = [item for item in items if item.status == status]
        return items

    def select_verified(self, category: str) -> Capability | None:
        candidates = self.find(category=category, status=CapabilityStatus.VERIFIED)
        if not candidates:
            return None
        return min(candidates, key=lambda item: (item.cost_weight, item.latency_ms))

    def snapshot(self) -> list[dict[str, object]]:
        return [
            item.model_dump(mode="json")
            for item in sorted(self._items.values(), key=lambda value: value.capability_id)
        ]
