from __future__ import annotations

from copy import deepcopy

import pytest

from creator_app.cognitive_runtime.event_bus import EventContractError, RuntimeEvent
from creator_app.cognitive_runtime.event_standards import (
    ASYNCAPI_VERSION,
    CLOUDEVENTS_CORE_RELEASE,
    CLOUDEVENTS_SPECVERSION,
    EventStandardsError,
    asyncapi_runtime_event_contract,
    to_cloudevent,
    validate_asyncapi_runtime_event_contract,
    validate_cloudevent_projection,
)

SUBJECT = "a" * 40


def _event(**overrides) -> RuntimeEvent:
    values = {
        "event_id": "evt-1",
        "event_type": "task.updated",
        "subject_sha": SUBJECT,
        "timestamp": "2026-08-27T05:00:00Z",
        "truth_class": "OBSERVED",
        "payload": {"progress": 1},
        "task_id": "task-1",
        "run_id": "run-1",
        "correlation_id": "corr-1",
    }
    values.update(overrides)
    return RuntimeEvent(**values)


def test_cloudevent_projection_preserves_ck_authority_bindings() -> None:
    event = _event()
    projected = to_cloudevent(event, expected_subject_sha=SUBJECT)
    assert projected["specversion"] == CLOUDEVENTS_SPECVERSION == "1.0"
    assert CLOUDEVENTS_CORE_RELEASE == "1.0.2"
    assert projected["id"] == event.event_id
    assert projected["cksubjectsha"] == SUBJECT
    assert projected["cktruthclass"] == "OBSERVED"
    assert projected["data"]["payload"] == {"progress": 1}
    validate_cloudevent_projection(event, projected, expected_subject_sha=SUBJECT)


def test_cloudevent_projection_rejects_wrong_subject() -> None:
    event = _event()
    with pytest.raises(EventContractError, match="subject mismatch"):
        to_cloudevent(event, expected_subject_sha="b" * 40)


def test_cloudevent_projection_cannot_strip_evidence_binding() -> None:
    event = _event(
        truth_class="VERIFIED",
        evidence_id="evd-1",
        output_digest="c" * 64,
    )
    projected = to_cloudevent(event, expected_subject_sha=SUBJECT)
    projected["data"]["evidence_id"] = ""
    with pytest.raises(EventStandardsError, match="evidence binding mismatch"):
        validate_cloudevent_projection(event, projected, expected_subject_sha=SUBJECT)


def test_cloudevent_projection_cannot_upgrade_truth() -> None:
    event = _event(truth_class="OBSERVED")
    projected = to_cloudevent(event, expected_subject_sha=SUBJECT)
    projected["cktruthclass"] = "VERIFIED"
    projected["data"]["truth_class"] = "VERIFIED"
    with pytest.raises(EventStandardsError, match="truth binding mismatch"):
        validate_cloudevent_projection(event, projected, expected_subject_sha=SUBJECT)


def test_verified_runtime_event_still_requires_ck_evidence() -> None:
    event = _event(truth_class="VERIFIED")
    with pytest.raises(EventContractError, match="verified event missing evidence binding"):
        to_cloudevent(event, expected_subject_sha=SUBJECT)


def test_asyncapi_contract_targets_3_1_0_and_cloud_events() -> None:
    contract = asyncapi_runtime_event_contract()
    assert contract["asyncapi"] == ASYNCAPI_VERSION == "3.1.0"
    assert contract["defaultContentType"] == "application/cloudevents+json"
    assert contract["channels"]["runtimeEvents"]["address"] == "ck-nexus/runtime/events"
    assert contract["x-ck-nexus-authority"]["cloudEventsRelease"] == "1.0.2"
    validate_asyncapi_runtime_event_contract(contract)


def test_asyncapi_stale_version_fails_closed() -> None:
    contract = asyncapi_runtime_event_contract()
    contract["asyncapi"] = "3.0.0"
    with pytest.raises(EventStandardsError, match="version mismatch"):
        validate_asyncapi_runtime_event_contract(contract)


def test_asyncapi_missing_channel_fails_closed() -> None:
    contract = asyncapi_runtime_event_contract()
    contract["channels"] = {}
    with pytest.raises(EventStandardsError, match="channel missing"):
        validate_asyncapi_runtime_event_contract(contract)


def test_asyncapi_cannot_enable_truth_upgrade_or_production_mutation() -> None:
    for key, expected in (
        ("truthUpgradeAllowed", "truth upgrade"),
        ("productionMutationAllowed", "production mutation"),
    ):
        contract = deepcopy(asyncapi_runtime_event_contract())
        contract["x-ck-nexus-authority"][key] = True
        with pytest.raises(EventStandardsError, match=expected):
            validate_asyncapi_runtime_event_contract(contract)
