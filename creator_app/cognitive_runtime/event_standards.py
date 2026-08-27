from __future__ import annotations

from typing import Any

from .event_bus import RuntimeEvent

CLOUDEVENTS_CORE_RELEASE = "1.0.2"
CLOUDEVENTS_SPECVERSION = "1.0"
ASYNCAPI_VERSION = "3.1.0"


class EventStandardsError(ValueError):
    """Raised when standards projection would weaken the CK event contract."""


def to_cloudevent(event: RuntimeEvent, *, expected_subject_sha: str) -> dict[str, Any]:
    """Project a validated CK RuntimeEvent into CloudEvents JSON shape.

    CK-NEXUS remains authoritative for truth/evidence semantics. CloudEvents is
    used only as an interoperability envelope and cannot upgrade truth state.
    """

    event.validate(expected_subject_sha)
    if not event.timestamp:
        raise EventStandardsError("runtime event timestamp is required")

    return {
        "specversion": CLOUDEVENTS_SPECVERSION,
        "id": event.event_id,
        "source": f"urn:ck-nexus:subject:{event.subject_sha}",
        "type": f"cknexus.{event.event_type}",
        "subject": event.task_id or event.subject_sha,
        "time": event.timestamp,
        "datacontenttype": "application/json",
        "cksubjectsha": event.subject_sha,
        "cktruthclass": event.truth_class,
        "ckcorrelationid": event.correlation_id,
        "ckcausationid": event.causation_id,
        "ckevidenceid": event.evidence_id,
        "data": {
            "event_type": event.event_type,
            "truth_class": event.truth_class,
            "task_id": event.task_id,
            "run_id": event.run_id,
            "node_id": event.node_id,
            "agent_id": event.agent_id,
            "input_digest": event.input_digest,
            "output_digest": event.output_digest,
            "evidence_id": event.evidence_id,
            "payload": event.payload,
        },
    }


def validate_cloudevent_projection(
    event: RuntimeEvent,
    projected: dict[str, Any],
    *,
    expected_subject_sha: str,
) -> None:
    """Fail closed if a projected CloudEvent loses CK authority bindings."""

    event.validate(expected_subject_sha)
    if projected.get("specversion") != CLOUDEVENTS_SPECVERSION:
        raise EventStandardsError("CloudEvents specversion mismatch")
    if projected.get("id") != event.event_id:
        raise EventStandardsError("CloudEvents event id mismatch")
    if projected.get("cksubjectsha") != event.subject_sha:
        raise EventStandardsError("CloudEvents subject binding mismatch")
    if projected.get("cktruthclass") != event.truth_class:
        raise EventStandardsError("CloudEvents truth binding mismatch")
    data = projected.get("data")
    if not isinstance(data, dict):
        raise EventStandardsError("CloudEvents data must be an object")
    if data.get("truth_class") != event.truth_class:
        raise EventStandardsError("CloudEvents data truth mismatch")
    if data.get("evidence_id") != event.evidence_id:
        raise EventStandardsError("CloudEvents evidence binding mismatch")
    if data.get("output_digest") != event.output_digest:
        raise EventStandardsError("CloudEvents output digest mismatch")


def asyncapi_runtime_event_contract() -> dict[str, Any]:
    """Return the machine-readable AsyncAPI contract for the CK event stream."""

    return {
        "asyncapi": ASYNCAPI_VERSION,
        "info": {
            "title": "CK-NEXUS Runtime Event Contract",
            "version": "1.0.0",
            "description": (
                "Development interoperability contract. CK-NEXUS remains the "
                "authority for event truth, evidence, policy and execution."
            ),
        },
        "defaultContentType": "application/cloudevents+json",
        "channels": {
            "runtimeEvents": {
                "address": "ck-nexus/runtime/events",
                "messages": {
                    "runtimeEvent": {
                        "$ref": "#/components/messages/runtimeEvent",
                    }
                },
            }
        },
        "operations": {
            "sendRuntimeEvent": {
                "action": "send",
                "channel": {"$ref": "#/channels/runtimeEvents"},
                "messages": [
                    {"$ref": "#/channels/runtimeEvents/messages/runtimeEvent"},
                ],
            }
        },
        "components": {
            "messages": {
                "runtimeEvent": {
                    "name": "runtimeEvent",
                    "title": "CK-NEXUS Runtime Event as CloudEvent",
                    "contentType": "application/cloudevents+json",
                    "payload": {
                        "type": "object",
                        "additionalProperties": True,
                        "required": [
                            "specversion",
                            "id",
                            "source",
                            "type",
                            "time",
                            "cksubjectsha",
                            "cktruthclass",
                            "data",
                        ],
                        "properties": {
                            "specversion": {"const": CLOUDEVENTS_SPECVERSION},
                            "id": {"type": "string", "minLength": 1},
                            "source": {"type": "string", "minLength": 1},
                            "type": {"type": "string", "pattern": "^cknexus\\."},
                            "subject": {"type": "string"},
                            "time": {"type": "string", "minLength": 1},
                            "cksubjectsha": {"type": "string", "minLength": 1},
                            "cktruthclass": {"type": "string", "minLength": 1},
                            "data": {"type": "object"},
                        },
                    },
                }
            }
        },
        "x-ck-nexus-authority": {
            "truthAuthority": "CK-NEXUS RuntimeEvent",
            "cloudEventsRelease": CLOUDEVENTS_CORE_RELEASE,
            "truthUpgradeAllowed": False,
            "productionMutationAllowed": False,
        },
    }


def validate_asyncapi_runtime_event_contract(document: dict[str, Any]) -> None:
    """Validate the non-negotiable CK-NEXUS AsyncAPI integration boundary."""

    if document.get("asyncapi") != ASYNCAPI_VERSION:
        raise EventStandardsError("AsyncAPI version mismatch")
    channels = document.get("channels")
    operations = document.get("operations")
    authority = document.get("x-ck-nexus-authority")
    if not isinstance(channels, dict) or "runtimeEvents" not in channels:
        raise EventStandardsError("runtimeEvents channel missing")
    if not isinstance(operations, dict) or "sendRuntimeEvent" not in operations:
        raise EventStandardsError("runtime event send operation missing")
    if not isinstance(authority, dict):
        raise EventStandardsError("CK authority extension missing")
    if authority.get("truthUpgradeAllowed") is not False:
        raise EventStandardsError("AsyncAPI contract must forbid truth upgrade")
    if authority.get("productionMutationAllowed") is not False:
        raise EventStandardsError("AsyncAPI contract must forbid production mutation")
