from __future__ import annotations

from dataclasses import dataclass, field

from .request import SkillExecutionRequest


@dataclass(slots=True)
class KillSwitchHierarchy:
    global_disabled: bool = False
    tenants: set[str] = field(default_factory=set)
    executors: set[str] = field(default_factory=set)
    skills: set[str] = field(default_factory=set)

    def reason(self, request: SkillExecutionRequest) -> str | None:
        if self.global_disabled:
            return "kill_switch_global"
        if request.tenant_id in self.tenants:
            return "kill_switch_tenant"
        if request.executor.value in self.executors:
            return "kill_switch_executor"
        if request.skill_id in self.skills:
            return "kill_switch_skill"
        return None
