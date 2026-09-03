from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ExecutionState(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    RETRY_WAIT = "RETRY_WAIT"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    REPAIRING = "REPAIRING"
    ROLLBACK = "ROLLBACK"
    RECOVERED = "RECOVERED"


ALLOWED_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.CREATED: frozenset({ExecutionState.PLANNING}),
    ExecutionState.PLANNING: frozenset({ExecutionState.READY, ExecutionState.BLOCKED, ExecutionState.FAILED}),
    ExecutionState.READY: frozenset({ExecutionState.RUNNING, ExecutionState.BLOCKED}),
    ExecutionState.RUNNING: frozenset({ExecutionState.VERIFYING, ExecutionState.RETRY_WAIT, ExecutionState.BLOCKED, ExecutionState.FAILED}),
    ExecutionState.RETRY_WAIT: frozenset({ExecutionState.RUNNING, ExecutionState.FAILED}),
    ExecutionState.VERIFYING: frozenset({ExecutionState.WAITING_APPROVAL, ExecutionState.DELIVERING, ExecutionState.REPAIRING, ExecutionState.FAILED}),
    ExecutionState.REPAIRING: frozenset({ExecutionState.VERIFYING, ExecutionState.ROLLBACK, ExecutionState.FAILED}),
    ExecutionState.ROLLBACK: frozenset({ExecutionState.RECOVERED, ExecutionState.FAILED}),
    ExecutionState.RECOVERED: frozenset({ExecutionState.DELIVERING, ExecutionState.COMPLETED}),
    ExecutionState.WAITING_APPROVAL: frozenset({ExecutionState.DELIVERING, ExecutionState.BLOCKED, ExecutionState.FAILED}),
    ExecutionState.DELIVERING: frozenset({ExecutionState.COMPLETED, ExecutionState.FAILED}),
    ExecutionState.COMPLETED: frozenset(),
    ExecutionState.BLOCKED: frozenset(),
    ExecutionState.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class WorkflowPattern:
    id: str
    version: str
    intent_tags: tuple[str, ...]
    agents: tuple[str, ...]
    allowed_tools: frozenset[str]
    forbidden_tools: frozenset[str]
    approval_policy: str
    side_effect_policy: str
    max_steps: int
    max_parallelism: int
    timeout_seconds: int
    evidence_requirements: tuple[str, ...] = ()
    output_schema: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> WorkflowPattern:
        required = {
            "id", "version", "intent_tags", "agents", "allowed_tools", "forbidden_tools",
            "approval_policy", "side_effect_policy", "max_steps", "timeout_seconds",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"pattern missing required keys: {', '.join(missing)}")
        max_steps = int(raw["max_steps"])
        max_parallelism = int(raw.get("max_parallelism", 1))
        timeout = int(raw["timeout_seconds"])
        if not (1 <= max_steps <= 100):
            raise ValueError("max_steps must be 1..100")
        if not (1 <= max_parallelism <= 20):
            raise ValueError("max_parallelism must be 1..20")
        if timeout < 1:
            raise ValueError("timeout_seconds must be positive")
        allowed = frozenset(map(str, raw["allowed_tools"]))
        forbidden = frozenset(map(str, raw["forbidden_tools"]))
        if allowed & forbidden:
            raise ValueError("a tool cannot be both allowed and forbidden")
        return cls(
            id=str(raw["id"]),
            version=str(raw["version"]),
            intent_tags=tuple(map(str, raw["intent_tags"])),
            agents=tuple(map(str, raw["agents"])),
            allowed_tools=allowed,
            forbidden_tools=forbidden,
            approval_policy=str(raw["approval_policy"]),
            side_effect_policy=str(raw["side_effect_policy"]),
            max_steps=max_steps,
            max_parallelism=max_parallelism,
            timeout_seconds=timeout,
            evidence_requirements=tuple(map(str, raw.get("evidence_requirements", []))),
            output_schema=raw.get("output_schema"),
        )


@dataclass(frozen=True, slots=True)
class PatternSelection:
    pattern_id: str | None
    version: str | None
    confidence: float
    reasons: tuple[str, ...]
    requires_human_approval: bool
    fallback_pattern: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    execution_id: str
    tenant_id: str
    actor_id: str
    roles: frozenset[str]
    permissions: frozenset[str]
    correlation_id: str
    environment: str
    policy_version: str
    pattern_id: str
    pattern_version: str
    max_steps: int
    timeout_seconds: int
    approval_state: str = "pending"
    idempotency_key: str | None = None
    input_trust: str = "trusted"
    input_taints: frozenset[str] = field(default_factory=frozenset)
    trusted_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class ToolRequest:
    step_id: str
    agent_id: str
    tool: str
    payload: dict[str, Any] = field(default_factory=dict)
    required_permission: str | None = None
    credential_scope: str | None = None
    requires_approval: bool = False
    side_effecting: bool = False
    memory_write: bool = False
    cross_agent_handoff: bool = False


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    allowed: bool
    code: str
    reason: str


@dataclass(slots=True)
class ExecutionRecord:
    context: ExecutionContext
    state: ExecutionState = ExecutionState.CREATED
    step_count: int = 0
    audit: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, target: ExecutionState, *, reason: str = "") -> None:
        allowed = ALLOWED_TRANSITIONS[self.state]
        if target not in allowed:
            raise ValueError(f"invalid execution transition {self.state} -> {target}")
        previous = self.state
        self.state = target
        self.audit.append({
            "event": "state_transition",
            "from": previous.value,
            "to": target.value,
            "reason": reason,
            "at": datetime.now(UTC).isoformat(),
            "pattern_id": self.context.pattern_id,
            "pattern_version": self.context.pattern_version,
            "execution_id": self.context.execution_id,
            "correlation_id": self.context.correlation_id,
        })


@dataclass(slots=True)
class ApprovalRecord:
    approval_id: str
    execution_id: str
    step_id: str
    requested_by: str
    required_role: str
    decision: str = "pending"
    decided_by: str | None = None
    reason: str | None = None
    expires_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
