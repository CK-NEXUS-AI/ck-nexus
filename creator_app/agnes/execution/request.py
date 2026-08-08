from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class ExecutorType(StrEnum):
    INTERNAL = "internal"
    PROVIDER = "provider"
    SANDBOX = "sandbox"
    WORKSPACE = "workspace"
    WORKSPACE_BROKER = "workspace_broker"
    RESEARCH = "research"
    MCP = "mcp_or_hosted"
    LEDGER = "ledger"
    CONTROLLER = "controller"


class ExecutorRiskClass(StrEnum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {
            ExecutorRiskClass.READ_ONLY: 0,
            ExecutorRiskClass.LOW: 1,
            ExecutorRiskClass.MEDIUM: 2,
            ExecutorRiskClass.HIGH: 3,
            ExecutorRiskClass.CRITICAL: 4,
        }[self]


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted((_freeze(v) for v in value), key=repr))
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(thaw(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class CredentialRequirement:
    credential_id: str
    consumer: str
    purpose: str


@dataclass(frozen=True, slots=True)
class SkillExecutionRequest:
    execution_id: str
    correlation_id: str
    skill_id: str
    skill_version: str
    executor: ExecutorType
    goal: str
    plan_step: Mapping[str, Any] = field(default_factory=dict)
    inputs: Mapping[str, Any] = field(default_factory=dict)
    tenant_id: str = "default"
    actor_id: str = "system"
    environment: str = "development"
    policy_version: str = "r14-phase1"
    workspace_id: str | None = None
    baseline_commit: str | None = None
    requires_approval: bool = False
    approval_id: str | None = None
    timeout_seconds: int = 300
    idempotency_key: str | None = None
    allowlist_paths: tuple[str, ...] = ()
    granted_capabilities: tuple[str, ...] = ()
    credential_requirements: tuple[CredentialRequirement, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_step", _freeze(dict(self.plan_step)))
        object.__setattr__(self, "inputs", _freeze(dict(self.inputs)))
        object.__setattr__(self, "allowlist_paths", tuple(self.allowlist_paths))
        object.__setattr__(self, "granted_capabilities", tuple(sorted(set(self.granted_capabilities))))
        object.__setattr__(self, "credential_requirements", tuple(self.credential_requirements))
        if not self.execution_id or not self.correlation_id or not self.skill_id:
            raise ValueError("execution_id, correlation_id, and skill_id are required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("unsupported execution environment")
