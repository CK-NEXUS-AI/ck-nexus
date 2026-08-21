from __future__ import annotations

from pydantic import BaseModel, Field

from creator_app.core.policy_errors import PolicyViolation
from creator_app.core.ultra_capability_governance import (
    CapabilityRecord,
    CapabilityState,
    UltraCapabilityRegistry,
    build_default_ultra_registry,
)


class UltraCommandResult(BaseModel):
    command: str
    status: str
    capability_id: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    executable: bool
    simulated: bool = False


class UltraCommandRouter:
    """Routes ULTRA slash commands through evidence-backed governance."""

    def __init__(self, registry: UltraCapabilityRegistry | None = None) -> None:
        self.registry = registry or build_default_ultra_registry()

    def execute(
        self,
        raw_command: str,
        *,
        governor_approved: bool = False,
    ) -> UltraCommandResult:
        command = raw_command.strip().split(maxsplit=1)[0].lower()
        record = self.registry.get(command)

        if record.state == CapabilityState.NOT_AVAILABLE:
            return self._result(record, executable=False)

        if record.state == CapabilityState.BLOCKED:
            raise PolicyViolation(f"{command} is blocked by CK-NEXUS governance")

        if record.governor_required and not governor_approved:
            raise PolicyViolation(f"{command} requires CK Governor approval")

        if record.mutation_capable:
            raise PolicyViolation(f"{command} mutation is not enabled in ULTRA governance V1")

        return self._result(
            record,
            executable=record.ready,
            simulated=record.state == CapabilityState.SIMULATED,
        )

    def help(self) -> list[UltraCommandResult]:
        return [
            self._result(
                record,
                executable=record.ready,
                simulated=record.state == CapabilityState.SIMULATED,
            )
            for record in self.registry.status()
        ]

    def status(self) -> dict[str, str]:
        return {
            record.command: self.registry.truthful_status(record.command)
            for record in self.registry.status()
        }

    @staticmethod
    def _result(
        record: CapabilityRecord,
        *,
        executable: bool,
        simulated: bool = False,
    ) -> UltraCommandResult:
        return UltraCommandResult(
            command=record.command,
            status=("READY_VERIFIED" if executable else record.state.value.upper()),
            capability_id=record.capability_id,
            description=record.description,
            evidence_ids=list(record.evidence_ids),
            executable=executable,
            simulated=simulated,
        )
