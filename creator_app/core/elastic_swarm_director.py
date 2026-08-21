from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from creator_app.core.consensus_engine import (
    AgentVote,
    ConsensusDecision,
    ConsensusEngine,
    ConsensusRule,
)
from creator_app.core.fanout_fanin_budget import (
    BudgetPolicy,
    FanoutFaninBudgetController,
)


class SwarmStatus(StrEnum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    SCALING = "scaling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SwarmTaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SwarmTask(BaseModel):
    task_id: str
    description: str = Field(min_length=1)
    required_capabilities: set[str] = Field(default_factory=set)
    estimated_cost: float = Field(default=0.0, ge=0)
    assigned_agent_id: str | None = None
    status: SwarmTaskStatus = SwarmTaskStatus.QUEUED


class WorkerOutcome(BaseModel):
    task_id: str
    agent_id: str
    success: bool
    output_ref: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    actual_cost: float = Field(default=0.0, ge=0)


class SwarmSnapshot(BaseModel):
    swarm_id: str
    status: SwarmStatus
    task_count: int
    completed_tasks: int
    failed_tasks: int
    active_tasks: int
    spent: float
    reserved: float


class ElasticSwarmDirector:
    """Coordinates task fan-out/fan-in under explicit budget and consensus rules."""

    def __init__(
        self,
        *,
        swarm_id: str,
        budget_policy: BudgetPolicy,
        max_worker_failures: int = 0,
    ) -> None:
        if not swarm_id.strip():
            raise ValueError("swarm_id is required")
        if max_worker_failures < 0:
            raise ValueError("max_worker_failures cannot be negative")
        self.swarm_id = swarm_id
        self.status = SwarmStatus.INITIALIZING
        self.max_worker_failures = max_worker_failures
        self.budget = FanoutFaninBudgetController(budget_policy)
        self._tasks: dict[str, SwarmTask] = {}
        self._reserved_costs: dict[str, float] = {}
        self._failure_count = 0

    def start(self) -> None:
        if self.status != SwarmStatus.INITIALIZING:
            raise ValueError("swarm can only start from INITIALIZING")
        self.status = SwarmStatus.RUNNING

    def cancel(self) -> None:
        if self.status in {SwarmStatus.COMPLETED, SwarmStatus.FAILED}:
            raise ValueError("terminal swarm cannot be cancelled")
        self.status = SwarmStatus.CANCELLED

    def decompose(
        self,
        *,
        parent_task_id: str,
        fragments: list[str],
        estimated_costs: list[float] | None = None,
    ) -> list[SwarmTask]:
        """Create deterministic subtasks from externally produced task fragments."""
        self._require_operational()
        if not parent_task_id.strip() or not fragments:
            raise ValueError("parent_task_id and at least one fragment are required")
        costs = estimated_costs or [0.0] * len(fragments)
        if len(costs) != len(fragments):
            raise ValueError("estimated_costs must match fragment count")

        created: list[SwarmTask] = []
        for index, description in enumerate(fragments, start=1):
            task_id = f"{parent_task_id}:{index}"
            if task_id in self._tasks:
                raise ValueError(f"duplicate task_id: {task_id}")
            task = SwarmTask(
                task_id=task_id,
                description=description,
                estimated_cost=costs[index - 1],
            )
            self._tasks[task_id] = task
            created.append(task.model_copy(deep=True))
        return created

    def add_task(self, task: SwarmTask) -> None:
        self._require_operational()
        if task.task_id in self._tasks:
            raise ValueError("task_id already exists")
        self._tasks[task.task_id] = task.model_copy(deep=True)

    def assign_worker(self, *, task_id: str, agent_id: str) -> SwarmTask:
        self._require_operational()
        task = self._require_task(task_id)
        if task.status != SwarmTaskStatus.QUEUED:
            raise ValueError("only queued tasks can receive worker assignments")
        if not agent_id.strip():
            raise ValueError("agent_id is required")
        task.assigned_agent_id = agent_id
        return task.model_copy(deep=True)

    def fan_out(self, task_ids: list[str]) -> list[SwarmTask]:
        """Reserve budget and mark assigned tasks RUNNING.

        Raises:
            ValueError: If assignment, state, concurrency, or budget checks fail.
        """
        self._require_operational()
        if not task_ids:
            raise ValueError("fan_out requires at least one task")

        pending = [self._require_task(task_id) for task_id in task_ids]
        if any(task.status != SwarmTaskStatus.QUEUED for task in pending):
            raise ValueError("fan_out only accepts queued tasks")
        if any(not task.assigned_agent_id for task in pending):
            raise ValueError("every fan_out task requires an assigned worker")

        active_workers = self._active_task_count()
        if active_workers + len(pending) > self.budget.policy.max_concurrent_workers:
            raise ValueError("fan_out exceeds concurrency policy")

        running: list[SwarmTask] = []
        try:
            for offset, task in enumerate(pending):
                self.budget.reserve(
                    task.estimated_cost,
                    active_workers=active_workers + offset,
                )
                self._reserved_costs[task.task_id] = task.estimated_cost
                task.status = SwarmTaskStatus.RUNNING
                running.append(task.model_copy(deep=True))
        except ValueError:
            self.status = SwarmStatus.FAILED
            raise

        if len(running) > 1:
            self.status = SwarmStatus.SCALING
        return running

    def fan_in(self, outcomes: list[WorkerOutcome]) -> list[SwarmTask]:
        """Settle worker outcomes and fail closed when failure threshold is exceeded."""
        self._require_operational(allow_scaling=True)
        if not outcomes:
            raise ValueError("fan_in requires at least one worker outcome")

        updated: list[SwarmTask] = []
        for outcome in outcomes:
            task = self._require_task(outcome.task_id)
            if task.status != SwarmTaskStatus.RUNNING:
                raise ValueError("worker outcome references a non-running task")
            if task.assigned_agent_id != outcome.agent_id:
                raise ValueError("worker outcome agent does not match assignment")
            if outcome.success and not outcome.evidence_ids:
                raise ValueError("successful worker outcome requires evidence")

            reserved_cost = self._reserved_costs.pop(task.task_id, 0.0)
            self.budget.settle(
                reserved_cost=reserved_cost,
                actual_cost=outcome.actual_cost,
            )
            task.status = (
                SwarmTaskStatus.COMPLETED
                if outcome.success
                else SwarmTaskStatus.FAILED
            )
            if not outcome.success:
                self._failure_count += 1
            updated.append(task.model_copy(deep=True))

        if self._failure_count > self.max_worker_failures:
            self.status = SwarmStatus.FAILED
        elif all(
            task.status in {SwarmTaskStatus.COMPLETED, SwarmTaskStatus.FAILED}
            for task in self._tasks.values()
        ):
            self.status = SwarmStatus.COMPLETED
        else:
            self.status = SwarmStatus.RUNNING
        return updated

    def gather_consensus(
        self,
        *,
        votes: list[AgentVote],
        rule: ConsensusRule,
    ) -> ConsensusDecision:
        self._require_operational(allow_scaling=True)
        return ConsensusEngine().evaluate(votes, rule=rule)

    def snapshot(self) -> SwarmSnapshot:
        tasks = list(self._tasks.values())
        return SwarmSnapshot(
            swarm_id=self.swarm_id,
            status=self.status,
            task_count=len(tasks),
            completed_tasks=sum(
                task.status == SwarmTaskStatus.COMPLETED for task in tasks
            ),
            failed_tasks=sum(task.status == SwarmTaskStatus.FAILED for task in tasks),
            active_tasks=sum(task.status == SwarmTaskStatus.RUNNING for task in tasks),
            spent=self.budget.spent,
            reserved=self.budget.reserved,
        )

    def _require_task(self, task_id: str) -> SwarmTask:
        if task_id not in self._tasks:
            raise KeyError(f"unknown swarm task: {task_id}")
        return self._tasks[task_id]

    def _active_task_count(self) -> int:
        return sum(
            task.status == SwarmTaskStatus.RUNNING for task in self._tasks.values()
        )

    def _require_operational(self, *, allow_scaling: bool = False) -> None:
        allowed = {SwarmStatus.RUNNING}
        if allow_scaling:
            allowed.add(SwarmStatus.SCALING)
        if self.status not in allowed:
            raise ValueError(f"swarm is not operational: {self.status}")
