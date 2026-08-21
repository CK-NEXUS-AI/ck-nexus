from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CapabilityState(StrEnum):
    VERIFIED = "verified"
    IMPLEMENTED_UNVERIFIED = "implemented_unverified"
    SIMULATED = "simulated"
    NOT_AVAILABLE = "not_available"
    BLOCKED = "blocked"


class CapabilityRecord(BaseModel):
    capability_id: str
    command: str
    description: str
    state: CapabilityState
    evidence_ids: list[str] = Field(default_factory=list)
    executor_available: bool = False
    mutation_capable: bool = False
    governor_required: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.state == CapabilityState.VERIFIED
            and bool(self.evidence_ids)
            and self.executor_available
            and not self.mutation_capable
        )


class UltraCapabilityRegistry:
    """Evidence-backed capability registry for NEXUS-OMNI ULTRA.

    The registry prevents persona/system-prompt claims from becoming runtime
    authority. A capability is READY only when implementation, executor and
    verification evidence are all present.
    """

    def __init__(self, records: list[CapabilityRecord] | None = None) -> None:
        self._records: dict[str, CapabilityRecord] = {}
        for record in records or []:
            self.register(record)

    def register(self, record: CapabilityRecord) -> None:
        if record.command in self._records:
            raise ValueError(f"duplicate command: {record.command}")
        self._records[record.command] = record

    def get(self, command: str) -> CapabilityRecord:
        normalized = command.strip().lower()
        if normalized not in self._records:
            return CapabilityRecord(
                capability_id=f"unknown:{normalized or 'empty'}",
                command=normalized,
                description="Capability is not registered",
                state=CapabilityState.NOT_AVAILABLE,
            )
        return self._records[normalized]

    def status(self) -> list[CapabilityRecord]:
        return [self._records[key] for key in sorted(self._records)]

    def truthful_status(self, command: str) -> str:
        record = self.get(command)
        if record.ready:
            return "READY_VERIFIED"
        if record.state == CapabilityState.VERIFIED:
            return "VERIFIED_NO_EXECUTOR"
        return record.state.value.upper()


def build_default_ultra_registry() -> UltraCapabilityRegistry:
    """Build conservative defaults from the current Post-P0 stack.

    Evidence IDs are development CI identities, not production release evidence.
    """

    records = [
        CapabilityRecord(
            capability_id="resilience.chaos",
            command="/chaos",
            description="Governed deterministic fault-plan simulation",
            state=CapabilityState.VERIFIED,
            evidence_ids=["dev-ci:test-standards-v1", "dev-ci:security-regression-v1"],
            executor_available=True,
            governor_required=True,
        ),
        CapabilityRecord(
            capability_id="resilience.formal",
            command="/formal",
            description="Lean 4 invariant verification",
            state=CapabilityState.VERIFIED,
            evidence_ids=["dev-ci:formal-verification"],
            executor_available=False,
        ),
        CapabilityRecord(
            capability_id="resilience.evidence",
            command="/evidence",
            description="Hash-linked append-only development evidence",
            state=CapabilityState.VERIFIED,
            evidence_ids=["dev-ci:test-standards-v1"],
            executor_available=True,
        ),
        CapabilityRecord(
            capability_id="system.status",
            command="/status",
            description="Report registered capability state without fabricated readiness",
            state=CapabilityState.VERIFIED,
            evidence_ids=["dev-ci:ck-nexus-ci"],
            executor_available=True,
        ),
        CapabilityRecord(
            capability_id="system.help",
            command="/help",
            description="List governed slash commands",
            state=CapabilityState.IMPLEMENTED_UNVERIFIED,
            executor_available=True,
        ),
        CapabilityRecord(
            capability_id="development.code",
            command="/code",
            description="Developer assistance mode; model capability, not runtime executor",
            state=CapabilityState.SIMULATED,
            executor_available=False,
        ),
        CapabilityRecord(
            capability_id="research.deep",
            command="/research",
            description="Research mode requires an attached research provider/tooling surface",
            state=CapabilityState.NOT_AVAILABLE,
        ),
        CapabilityRecord(
            capability_id="business.sales",
            command="/sales",
            description="Autonomous sales execution is not enabled by this layer",
            state=CapabilityState.BLOCKED,
            mutation_capable=True,
            governor_required=True,
        ),
        CapabilityRecord(
            capability_id="cognitive.think",
            command="/think",
            description="Reasoning assistance without exposing private chain-of-thought",
            state=CapabilityState.SIMULATED,
            executor_available=False,
        ),
    ]
    return UltraCapabilityRegistry(records)
