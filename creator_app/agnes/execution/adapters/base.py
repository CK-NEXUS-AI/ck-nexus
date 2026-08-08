from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..credentials import CredentialLeaseBundle
from ..manifest import ImmutableExecutionManifest
from ..request import ExecutorRiskClass, SkillExecutionRequest
from ..result import SkillExecutionResult


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    manifest: ImmutableExecutionManifest
    credentials: CredentialLeaseBundle


class SkillExecutor(Protocol):
    name: str
    executor_type: str
    risk_class: ExecutorRiskClass

    async def can_handle(self, request: SkillExecutionRequest) -> bool: ...

    async def execute(
        self,
        request: SkillExecutionRequest,
        context: ExecutionContext,
    ) -> SkillExecutionResult: ...

    async def health(self) -> dict[str, object]: ...
