from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BudgetLevel(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class BudgetPolicy(BaseModel):
    total_budget: float = Field(gt=0)
    max_concurrent_workers: int = Field(gt=0)
    warning_threshold: float = Field(default=0.50, ge=0, le=1)
    critical_threshold: float = Field(default=0.80, ge=0, le=1)
    exhausted_threshold: float = Field(default=0.95, ge=0, le=1)

    def model_post_init(self, __context: object) -> None:
        if not (
            self.warning_threshold
            < self.critical_threshold
            < self.exhausted_threshold
        ):
            raise ValueError("budget thresholds must be strictly increasing")


class BudgetSnapshot(BaseModel):
    total_budget: float
    spent: float
    reserved: float
    utilization: float
    level: BudgetLevel
    cheapest_model_only: bool


class FanoutFaninBudgetController:
    """Tracks swarm budget and concurrency using fail-closed reservation rules."""

    def __init__(self, policy: BudgetPolicy) -> None:
        self.policy = policy
        self._spent = 0.0
        self._reserved = 0.0

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def reserved(self) -> float:
        return self._reserved

    @property
    def utilization(self) -> float:
        return (self._spent + self._reserved) / self.policy.total_budget

    @property
    def level(self) -> BudgetLevel:
        utilization = self.utilization
        if utilization >= self.policy.exhausted_threshold:
            return BudgetLevel.EXHAUSTED
        if utilization >= self.policy.critical_threshold:
            return BudgetLevel.CRITICAL
        if utilization >= self.policy.warning_threshold:
            return BudgetLevel.WARNING
        return BudgetLevel.HEALTHY

    @property
    def cheapest_model_only(self) -> bool:
        return self.level == BudgetLevel.EXHAUSTED

    def can_dispatch(self, *, estimated_cost: float, active_workers: int) -> bool:
        if estimated_cost < 0 or active_workers < 0:
            return False
        if active_workers >= self.policy.max_concurrent_workers:
            return False
        projected = self._spent + self._reserved + estimated_cost
        return projected <= self.policy.total_budget

    def reserve(self, estimated_cost: float, *, active_workers: int) -> None:
        """Reserve cost before dispatching work.

        Raises:
            ValueError: If the reservation would exceed cost or concurrency limits.
        """
        if not self.can_dispatch(
            estimated_cost=estimated_cost,
            active_workers=active_workers,
        ):
            raise ValueError("dispatch rejected by swarm budget policy")
        self._reserved += estimated_cost

    def settle(self, *, reserved_cost: float, actual_cost: float) -> None:
        """Convert a reservation into actual spend.

        Raises:
            ValueError: If costs are invalid or final spend would exceed budget.
        """
        if reserved_cost < 0 or actual_cost < 0:
            raise ValueError("cost values must be non-negative")
        if reserved_cost > self._reserved:
            raise ValueError("cannot settle more than reserved cost")
        projected_spend = self._spent + actual_cost
        if projected_spend > self.policy.total_budget:
            raise ValueError("actual cost would exceed swarm budget")
        self._reserved -= reserved_cost
        self._spent = projected_spend

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            total_budget=self.policy.total_budget,
            spent=self._spent,
            reserved=self._reserved,
            utilization=self.utilization,
            level=self.level,
            cheapest_model_only=self.cheapest_model_only,
        )
