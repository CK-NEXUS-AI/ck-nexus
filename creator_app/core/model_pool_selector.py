from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ModelStatus(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ModelRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SelectionStrategy(StrEnum):
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    BALANCED = "balanced"
    LATENCY_OPTIMIZED = "latency_optimized"


class ModelRecord(BaseModel):
    model_id: str
    provider: str
    capabilities: set[str] = Field(default_factory=set)
    cost_per_1k_tokens: float = Field(ge=0)
    latency_ms: int = Field(gt=0)
    quality_score: float = Field(ge=0, le=1)
    risk_allowed: set[ModelRiskLevel] = Field(default_factory=set)
    status: ModelStatus = ModelStatus.AVAILABLE


class ModelSelectionCriteria(BaseModel):
    task_complexity: float = Field(default=0.5, ge=0, le=1)
    required_capabilities: set[str] = Field(default_factory=set)
    budget_limit: float | None = Field(default=None, ge=0)
    latency_requirement_ms: int | None = Field(default=None, gt=0)
    risk_level: ModelRiskLevel = ModelRiskLevel.LOW
    estimated_tokens: int = Field(default=1000, ge=0)
    strategy: SelectionStrategy = SelectionStrategy.BALANCED


class ModelSelection(BaseModel):
    primary: ModelRecord
    fallbacks: list[ModelRecord] = Field(default_factory=list)


class ModelPoolSelector:
    """Selects provider-neutral model records using policy-safe deterministic rules."""

    def __init__(self, *, circuit_breaker_threshold: int = 3) -> None:
        if circuit_breaker_threshold <= 0:
            raise ValueError("circuit_breaker_threshold must be positive")
        self._models: dict[str, ModelRecord] = {}
        self._provider_failures: dict[str, int] = {}
        self._open_providers: set[str] = set()
        self._circuit_breaker_threshold = circuit_breaker_threshold

    def register(self, model: ModelRecord) -> None:
        self._models[model.model_id] = model.model_copy(deep=True)

    def record_provider_failure(self, provider: str) -> None:
        failures = self._provider_failures.get(provider, 0) + 1
        self._provider_failures[provider] = failures
        if failures >= self._circuit_breaker_threshold:
            self._open_providers.add(provider)

    def reset_provider(self, provider: str) -> None:
        self._provider_failures[provider] = 0
        self._open_providers.discard(provider)

    def provider_circuit_open(self, provider: str) -> bool:
        return provider in self._open_providers

    def select(self, criteria: ModelSelectionCriteria) -> ModelSelection:
        candidates = [
            model
            for model in self._models.values()
            if self._eligible(model, criteria)
        ]
        if not candidates:
            raise LookupError("no eligible model satisfies selection criteria")
        ranked = sorted(candidates, key=lambda model: self._sort_key(model, criteria))
        return ModelSelection(primary=ranked[0], fallbacks=ranked[1:])

    def _eligible(self, model: ModelRecord, criteria: ModelSelectionCriteria) -> bool:
        if model.status == ModelStatus.UNAVAILABLE:
            return False
        if self.provider_circuit_open(model.provider):
            return False
        if not criteria.required_capabilities.issubset(model.capabilities):
            return False
        if criteria.risk_level not in model.risk_allowed:
            return False
        estimated_cost = self._estimated_cost(model, criteria.estimated_tokens)
        if criteria.budget_limit is not None and estimated_cost > criteria.budget_limit:
            return False
        if (
            criteria.latency_requirement_ms is not None
            and model.latency_ms > criteria.latency_requirement_ms
        ):
            return False
        return True

    @staticmethod
    def _estimated_cost(model: ModelRecord, estimated_tokens: int) -> float:
        return model.cost_per_1k_tokens * estimated_tokens / 1000

    def _sort_key(
        self,
        model: ModelRecord,
        criteria: ModelSelectionCriteria,
    ) -> tuple[float, float, float]:
        cost = self._estimated_cost(model, criteria.estimated_tokens)
        if criteria.strategy == SelectionStrategy.COST_OPTIMIZED:
            return (cost, -model.quality_score, float(model.latency_ms))
        if criteria.strategy == SelectionStrategy.QUALITY_OPTIMIZED:
            return (-model.quality_score, cost, float(model.latency_ms))
        if criteria.strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            return (float(model.latency_ms), cost, -model.quality_score)
        quality_penalty = 1 - model.quality_score
        complexity_weight = 0.5 + criteria.task_complexity / 2
        balanced = cost + quality_penalty * complexity_weight
        return (balanced, float(model.latency_ms), cost)
