from __future__ import annotations

from collections import defaultdict

from .adapters.base import SkillExecutor
from .request import ExecutorType, SkillExecutionRequest


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[ExecutorType, list[SkillExecutor]] = defaultdict(list)

    def register(self, executor: SkillExecutor) -> None:
        self._executors[ExecutorType(executor.executor_type)].append(executor)

    async def resolve(self, request: SkillExecutionRequest) -> SkillExecutor | None:
        for executor in self._executors.get(request.executor, []):
            if await executor.can_handle(request):
                return executor
        return None

    def status(self) -> dict[str, object]:
        return {
            "registered": {
                key.value: [executor.name for executor in value]
                for key, value in self._executors.items()
            }
        }
