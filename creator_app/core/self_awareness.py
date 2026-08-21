from __future__ import annotations

from pydantic import BaseModel, Field

from .capability_registry import CapabilityRegistry, CapabilityStatus


class SelfAwarenessSnapshot(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
    production_ready: bool = False


class SelfAwarenessEngine:
    """Derive capability strengths and limits from the evidence-bound registry."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def snapshot(self) -> SelfAwarenessSnapshot:
        strengths: list[str] = []
        limitations: list[str] = []
        blocked: list[str] = []

        for item in self._registry.snapshot():
            capability_id = str(item["capability_id"])
            status = CapabilityStatus(str(item["status"]))
            if status == CapabilityStatus.VERIFIED:
                strengths.append(capability_id)
            elif status == CapabilityStatus.BLOCKED:
                blocked.append(capability_id)
            else:
                limitations.append(capability_id)

        return SelfAwarenessSnapshot(
            strengths=sorted(strengths),
            limitations=sorted(limitations),
            blocked=sorted(blocked),
            production_ready=False,
        )
