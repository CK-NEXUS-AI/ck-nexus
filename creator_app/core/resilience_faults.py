from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from creator_app.core.policy_errors import PolicyViolation


class FaultType(StrEnum):
    SERVICE_UNAVAILABLE = "service_unavailable"
    LATENCY = "latency"
    NETWORK_PARTITION = "network_partition"
    DISK_FULL = "disk_full"
    CPU_PRESSURE = "cpu_pressure"
    MEMORY_PRESSURE = "memory_pressure"


class FaultTarget(StrEnum):
    CORE = "core"
    REDIS = "redis"
    POSTGRES = "postgres"
    PROVIDER = "provider"
    STATE_STORE = "state_store"


class FaultSpec(BaseModel):
    fault_id: str = Field(min_length=1)
    fault_type: FaultType
    target: FaultTarget
    severity: int = Field(default=1, ge=1, le=3)
    duration_ms: int = Field(default=1000, ge=1, le=30000)


class FaultPlan(BaseModel):
    seed: int
    faults: list[FaultSpec]
    sandbox_attested: bool = False
    execution_grant_id: str | None = None

    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class FaultAdapter(Protocol):
    def inject(self, fault: FaultSpec) -> dict[str, object]: ...


class FaultInjectionPolicy:
    """Controls whether a chaos plan may execute.

    No host process, network, disk, or service mutation is performed here. Runtime-specific
    adapters must be sandboxed and explicitly granted before this policy will dispatch faults.
    """

    @staticmethod
    def require_allowed(plan: FaultPlan) -> None:
        if not plan.sandbox_attested:
            raise PolicyViolation("chaos execution requires sandbox attestation")
        if not plan.execution_grant_id:
            raise PolicyViolation("chaos execution requires an execution grant")
        if not plan.faults:
            raise PolicyViolation("chaos plan must contain at least one fault")


class ChaosScenarioRunner:
    """Executes a deterministic fault plan through an injected sandbox adapter."""

    def __init__(self, adapter: FaultAdapter) -> None:
        self._adapter = adapter

    def run(self, plan: FaultPlan) -> list[dict[str, object]]:
        FaultInjectionPolicy.require_allowed(plan)
        return [self._adapter.inject(fault) for fault in plan.faults]
