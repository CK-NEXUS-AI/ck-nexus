from __future__ import annotations

from dataclasses import dataclass

from .capabilities import ResolvedCapability
from .request import ExecutorRiskClass, ExecutorType, SkillExecutionRequest


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    reason: str
    missing: tuple[str, ...] = ()


class PermissionResolver:
    """Explicit capability grants for executable/non-read-only work.

    Internal read-only planning/policy skills can run without an explicit capability grant.
    All other execution surfaces require the caller/controller to grant every declared capability.
    """

    _implicit_read_only_executors = {ExecutorType.INTERNAL, ExecutorType.LEDGER}

    def evaluate(
        self,
        request: SkillExecutionRequest,
        resolved: ResolvedCapability,
        risk_class: ExecutorRiskClass,
    ) -> PermissionDecision:
        if (
            risk_class is ExecutorRiskClass.READ_ONLY
            and request.executor in self._implicit_read_only_executors
        ):
            return PermissionDecision(True, "implicit_internal_read_only")
        granted = set(request.granted_capabilities)
        missing = tuple(sorted(set(resolved.capabilities) - granted))
        if missing:
            return PermissionDecision(False, "missing_capability_grant", missing)
        return PermissionDecision(True, "explicit_capability_grant")
