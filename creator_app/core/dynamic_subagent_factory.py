from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentRole(StrEnum):
    RESEARCHER = "researcher"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    CHALLENGER = "challenger"
    EVALUATOR = "evaluator"


class AgentLifecycle(StrEnum):
    CREATED = "created"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    RETIRED = "retired"


class AgentRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentSpec(BaseModel):
    agent_id: str
    role: AgentRole
    capabilities: set[str] = Field(default_factory=set)
    risk_level: AgentRiskLevel = AgentRiskLevel.LOW
    model_requirements: set[str] = Field(default_factory=set)
    max_runtime_seconds: int = Field(default=300, gt=0)
    max_cost: float = Field(default=1.0, ge=0)
    context_id: str


class SubagentRecord(BaseModel):
    spec: AgentSpec
    lifecycle: AgentLifecycle = AgentLifecycle.CREATED
    assigned_task_id: str | None = None
    resources_released: bool = False


class DynamicSubagentFactory:
    """Creates isolated, typed subagent records without binding to any provider SDK."""

    def __init__(self) -> None:
        self._agents: dict[str, SubagentRecord] = {}

    def create(self, spec: AgentSpec) -> SubagentRecord:
        if spec.agent_id in self._agents:
            raise ValueError("agent_id already exists")
        record = SubagentRecord(spec=spec)
        self._agents[spec.agent_id] = record
        return record.model_copy(deep=True)

    def _role_spec(
        self,
        *,
        agent_id: str,
        role: AgentRole,
        capabilities: set[str],
        model_requirements: set[str] | None = None,
        risk_level: AgentRiskLevel = AgentRiskLevel.LOW,
        max_runtime_seconds: int = 300,
        max_cost: float = 1.0,
    ) -> AgentSpec:
        return AgentSpec(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities,
            model_requirements=model_requirements or set(),
            risk_level=risk_level,
            max_runtime_seconds=max_runtime_seconds,
            max_cost=max_cost,
            context_id=f"context:{agent_id}",
        )

    def create_researcher(self, *, agent_id: str) -> SubagentRecord:
        return self.create(
            self._role_spec(
                agent_id=agent_id,
                role=AgentRole.RESEARCHER,
                capabilities={"research", "synthesis"},
            )
        )

    def create_builder(self, *, agent_id: str) -> SubagentRecord:
        return self.create(
            self._role_spec(
                agent_id=agent_id,
                role=AgentRole.BUILDER,
                capabilities={"code", "build"},
                risk_level=AgentRiskLevel.MEDIUM,
            )
        )

    def create_reviewer(self, *, agent_id: str) -> SubagentRecord:
        return self.create(
            self._role_spec(
                agent_id=agent_id,
                role=AgentRole.REVIEWER,
                capabilities={"review", "verification"},
            )
        )

    def create_challenger(self, *, agent_id: str) -> SubagentRecord:
        return self.create(
            self._role_spec(
                agent_id=agent_id,
                role=AgentRole.CHALLENGER,
                capabilities={"critique", "adversarial_review"},
            )
        )

    def create_evaluator(self, *, agent_id: str) -> SubagentRecord:
        return self.create(
            self._role_spec(
                agent_id=agent_id,
                role=AgentRole.EVALUATOR,
                capabilities={"evaluation", "scoring"},
            )
        )

    def assign(self, *, agent_id: str, task_id: str) -> SubagentRecord:
        record = self._require_active(agent_id)
        if record.lifecycle != AgentLifecycle.CREATED:
            raise ValueError("agent must be in CREATED state before assignment")
        record.lifecycle = AgentLifecycle.ASSIGNED
        record.assigned_task_id = task_id
        return record.model_copy(deep=True)

    def mark_executing(self, *, agent_id: str) -> SubagentRecord:
        record = self._require_active(agent_id)
        if record.lifecycle != AgentLifecycle.ASSIGNED:
            raise ValueError("agent must be assigned before execution")
        record.lifecycle = AgentLifecycle.EXECUTING
        return record.model_copy(deep=True)

    def retire(self, *, agent_id: str) -> SubagentRecord:
        record = self._require_active(agent_id)
        record.lifecycle = AgentLifecycle.RETIRED
        record.assigned_task_id = None
        record.resources_released = True
        return record.model_copy(deep=True)

    def get(self, agent_id: str) -> SubagentRecord:
        if agent_id not in self._agents:
            raise KeyError(f"unknown agent: {agent_id}")
        return self._agents[agent_id].model_copy(deep=True)

    def _require_active(self, agent_id: str) -> SubagentRecord:
        if agent_id not in self._agents:
            raise KeyError(f"unknown agent: {agent_id}")
        record = self._agents[agent_id]
        if record.lifecycle == AgentLifecycle.RETIRED:
            raise ValueError("retired agent cannot be reused")
        return record
