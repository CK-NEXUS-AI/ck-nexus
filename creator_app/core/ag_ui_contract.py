from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class UIEventType(StrEnum):
    RUN_STARTED = "run.started"
    STATE_SNAPSHOT = "state.snapshot"
    STATE_DELTA = "state.delta"
    TOOL_OUTPUT = "tool.output"
    APPROVAL_REQUIRED = "approval.required"
    STEERING_APPLIED = "steering.applied"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


class UIComponentKind(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"
    METRIC = "metric"
    TABLE = "table"
    CHART = "chart"
    FORM = "form"
    APPROVAL = "approval"
    PROGRESS = "progress"
    ARTIFACT = "artifact"
    AGENT_TREE = "agent_tree"


class SteeringAction(StrEnum):
    PAUSE = "pause"
    CANCEL = "cancel"
    PRIORITIZE = "prioritize"
    CLARIFY = "clarify"


class GenerativeUIComponent(BaseModel):
    component_id: str = Field(min_length=1, max_length=128)
    kind: UIComponentKind
    content_digest: str | None = None
    data_digest: str | None = None
    artifact_ref: str | None = None
    interactive: bool = False
    approval_required: bool = False
    evidence_ids: tuple[str, ...] = ()


class UIEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: UIEventType
    task_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=0)
    state_digest: str | None = None
    previous_state_digest: str | None = None
    component: GenerativeUIComponent | None = None
    causation_id: str | None = None
    evidence_ids: tuple[str, ...] = ()


class SteeringCommand(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    action: SteeringAction
    payload_digest: str | None = None
    governor_approval_id: str | None = None
    production_mutation_requested: bool = False


class AGUIContract:
    """Typed UI/event contract. Commands request change; only events mutate visible state."""

    @staticmethod
    def component_allowed(component: GenerativeUIComponent) -> bool:
        if not component.evidence_ids:
            return False
        if not any((component.content_digest, component.data_digest, component.artifact_ref)):
            return False
        if component.interactive and component.kind not in {
            UIComponentKind.FORM,
            UIComponentKind.APPROVAL,
        }:
            return False
        if component.approval_required and not component.interactive:
            return False
        return True

    @staticmethod
    def steering_allowed(command: SteeringCommand) -> bool:
        if command.production_mutation_requested:
            return False
        if command.action in {SteeringAction.CANCEL, SteeringAction.PRIORITIZE}:
            return bool(command.governor_approval_id)
        return True

    @staticmethod
    def validate_event_stream(events: list[UIEvent]) -> bool:
        if not events:
            return False
        run_ids = {event.run_id for event in events}
        task_ids = {event.task_id for event in events}
        event_ids = [event.event_id for event in events]
        if len(run_ids) != 1 or len(task_ids) != 1:
            return False
        if len(event_ids) != len(set(event_ids)):
            return False
        sequences = [event.sequence for event in events]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            return False
        for event in events:
            if event.component is not None and not AGUIContract.component_allowed(event.component):
                return False
            if event.event_type in {UIEventType.STATE_SNAPSHOT, UIEventType.STATE_DELTA}:
                if not event.state_digest or not event.evidence_ids:
                    return False
            if event.event_type == UIEventType.STATE_DELTA and not event.previous_state_digest:
                return False
        return True
