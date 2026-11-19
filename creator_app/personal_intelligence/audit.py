"""Privacy-safe audit envelopes for personal intelligence operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class PersonalAuditEvent:
    event_id: str
    timestamp: str
    action: str
    capability: str
    decision: str
    purpose: str
    resource_ref: str | None
    content_digest: str | None
    raw_content_stored: bool = False


def build_audit_event(
    *,
    action: str,
    capability: str,
    decision: str,
    purpose: str,
    resource_ref: str | None = None,
    content: bytes | None = None,
) -> PersonalAuditEvent:
    """Create an event with a digest rather than retaining raw personal content."""
    timestamp = datetime.now(UTC).isoformat()
    digest = hashlib.sha256(content).hexdigest() if content is not None else None
    material = json.dumps(
        {
            "timestamp": timestamp,
            "action": action,
            "capability": capability,
            "decision": decision,
            "purpose": purpose,
            "resource_ref": resource_ref,
            "content_digest": digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return PersonalAuditEvent(
        event_id=f"pae-{hashlib.sha256(material).hexdigest()[:20]}",
        timestamp=timestamp,
        action=action,
        capability=capability,
        decision=decision,
        purpose=purpose,
        resource_ref=resource_ref,
        content_digest=digest,
    )


def event_dict(event: PersonalAuditEvent) -> dict[str, str | bool | None]:
    return asdict(event)
