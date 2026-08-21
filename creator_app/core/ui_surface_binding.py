from __future__ import annotations

from pydantic import BaseModel, Field

from creator_app.core.computer_use_contract import ComputerEnvironment
from creator_app.core.realtime_multimodal import RealtimeModality, RealtimeSession


class UISurfaceBinding(BaseModel):
    binding_id: str = Field(min_length=1, max_length=128)
    environment: ComputerEnvironment
    task_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    screen_digest: str | None = None
    realtime_session_id: str | None = None
    requested_modalities: set[RealtimeModality] = Field(default_factory=set)
    prompt_injection_evidence_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    production_mutation_allowed: bool = False


class UISurfaceBindingPolicy:
    """Reuse Gen 6.1 computer/realtime authority rather than creating a second executor."""

    @staticmethod
    def bindable(
        binding: UISurfaceBinding,
        *,
        realtime_session: RealtimeSession | None = None,
    ) -> bool:
        if binding.production_mutation_allowed or not binding.evidence_ids:
            return False
        if binding.environment in {
            ComputerEnvironment.BROWSER,
            ComputerEnvironment.DESKTOP,
            ComputerEnvironment.MOBILE,
        }:
            if not binding.screen_digest or not binding.prompt_injection_evidence_ids:
                return False
        if binding.requested_modalities:
            if realtime_session is None:
                return False
            if binding.realtime_session_id != realtime_session.session_id:
                return False
            available = realtime_session.input_modalities | realtime_session.output_modalities
            if not binding.requested_modalities.issubset(available):
                return False
            if not realtime_session.evidence_ids:
                return False
        return True
