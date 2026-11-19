from __future__ import annotations

from dataclasses import dataclass

from creator_app.agnes_skills import SkillDefinition

from .request import ExecutorType, SkillExecutionRequest


class CapabilityResolutionError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedCapability:
    skill_id: str
    executor: ExecutorType
    capabilities: tuple[str, ...]


class CapabilityResolver:
    def resolve(
        self,
        request: SkillExecutionRequest,
        skill: SkillDefinition,
    ) -> ResolvedCapability:
        if request.executor.value != skill.executor:
            raise CapabilityResolutionError("executor_manifest_mismatch")
        if not skill.capabilities:
            raise CapabilityResolutionError("skill_has_no_declared_capability")
        return ResolvedCapability(skill.id, request.executor, tuple(skill.capabilities))
