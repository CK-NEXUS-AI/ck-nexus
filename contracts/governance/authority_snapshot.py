from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .capability_lease import CapabilityLease


class BudgetSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    remaining_calls: int = Field(ge=0)
    remaining_mutations: int = Field(ge=0)
    remaining_cost_usd: Decimal = Field(ge=Decimal("0"))
    remaining_cpu_ms: int = Field(ge=0)
    remaining_memory_mb: int = Field(ge=0)


class AuthoritySnapshot(BaseModel):
    """Immutable authorization-time snapshot; never mutate after authorization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lease: CapabilityLease
    policy_decision: dict[str, Any]
    approval_ref: str | None = None
    sandbox_policy: dict[str, Any]
    credential_refs: tuple[str, ...] = ()
    budget_remaining: BudgetSnapshot
    authorized_at: datetime
    expires_at: datetime | None = None
    snapshot_hash: str = Field(min_length=1)
