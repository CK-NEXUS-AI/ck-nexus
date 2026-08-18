from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Budget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_calls: int = Field(ge=0)
    max_mutations: int = Field(ge=0)
    max_cost_usd: Decimal = Field(ge=Decimal("0"))
    max_cpu_ms: int = Field(ge=0)
    max_memory_mb: int = Field(ge=0)
    max_wall_ms: int = Field(ge=0)


class Consumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calls: int = Field(default=0, ge=0)
    mutations: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    cpu_ms: int = Field(default=0, ge=0)
    memory_peak_mb: int = Field(default=0, ge=0)


class CapabilityLease(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lease_id: UUID
    tenant_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    scopes: tuple[str, ...] = ()
    budgets: Budget
    consumption: Consumption = Consumption()
    issued_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    approval_ref: str | None = None
    policy_decision_id: str | None = None
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_times(self) -> "CapabilityLease":
        if self.expires_at and self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.revoked_at and self.revoked_at < self.issued_at:
            raise ValueError("revoked_at cannot precede issued_at")
        return self

    def active(self, now: datetime) -> bool:
        if self.revoked_at is not None and now >= self.revoked_at:
            return False
        if self.expires_at is not None and now >= self.expires_at:
            return False
        return now >= self.issued_at

    def within_budget(self, *, calls: int = 0, mutations: int = 0,
                      cost_usd: Decimal = Decimal("0"), cpu_ms: int = 0,
                      memory_mb: int = 0) -> bool:
        c = self.consumption
        b = self.budgets
        return (
            c.calls + calls <= b.max_calls
            and c.mutations + mutations <= b.max_mutations
            and c.cost_usd + cost_usd <= b.max_cost_usd
            and c.cpu_ms + cpu_ms <= b.max_cpu_ms
            and c.memory_peak_mb + memory_mb <= b.max_memory_mb
        )
