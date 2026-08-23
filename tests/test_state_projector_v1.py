from __future__ import annotations

import pytest

from creator_app.cognitive_runtime.event_bus import (
    EventContractError,
    RuntimeEvent,
    RuntimeEventBus,
)
from creator_app.cognitive_runtime.state_projector import StateProjector

SUBJECT = "5f98f23c6841e6f335e9a114e8b0c0e4201b4850"


def ev(event_id: str, event_type: str, timestamp: str, **kwargs) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        event_type=event_type,
        subject_sha=kwargs.pop("subject_sha", SUBJECT),
        timestamp=timestamp,
        truth_class=kwargs.pop("truth_class", "OBSERVED"),
        payload=kwargs.pop("payload", {"status": "ok"}),
        **kwargs,
    )


def test_duplicate_event_is_idempotent() -> None:
    bus = RuntimeEventBus(SUBJECT)
    event = ev("evt-1", "task.started", "2026-08-23T01:00:00Z", task_id="t1")
    assert bus.append(event) is True
    assert bus.append(event) is False
    assert len(bus.events()) == 1


def test_conflicting_duplicate_rejected() -> None:
    bus = RuntimeEventBus(SUBJECT)
    bus.append(ev("evt-1", "task.started", "2026-08-23T01:00:00Z", task_id="t1"))
    with pytest.raises(EventContractError, match="conflicting duplicate"):
        bus.append(ev("evt-1", "task.completed", "2026-08-23T01:00:01Z", task_id="t1"))


def test_subject_mismatch_rejected() -> None:
    bus = RuntimeEventBus(SUBJECT)
    with pytest.raises(EventContractError, match="subject mismatch"):
        bus.append(
            ev(
                "evt-2",
                "task.started",
                "2026-08-23T01:00:00Z",
                task_id="t1",
                subject_sha="0" * 40,
            )
        )


def test_verified_requires_evidence_binding() -> None:
    bus = RuntimeEventBus(SUBJECT)
    with pytest.raises(EventContractError, match="missing evidence"):
        bus.append(
            ev(
                "evt-3",
                "verification.completed",
                "2026-08-23T01:00:00Z",
                truth_class="VERIFIED",
            )
        )


def test_out_of_order_replay_is_deterministic() -> None:
    projector = StateProjector(SUBJECT)
    first = ev("evt-a", "task.started", "2026-08-23T01:00:00Z", task_id="t1")
    second = ev("evt-b", "task.completed", "2026-08-23T01:00:02Z", task_id="t1")
    state_a = projector.project([second, first])
    state_b = projector.project([first, second])
    assert state_a == state_b
    assert state_a["tasks"]["t1"]["event_type"] == "task.completed"


def test_valid_verified_event_promotes_public_truth() -> None:
    projector = StateProjector(SUBJECT)
    verified = ev(
        "evt-v",
        "verification.completed",
        "2026-08-23T01:00:03Z",
        truth_class="VERIFIED",
        evidence_id="evd-1",
        output_digest="a" * 64,
    )
    state = projector.project([verified])
    assert state["truth"] == "VERIFIED"
    assert state["event_count"] == 1
    assert len(state["projection_digest"]) == 64
