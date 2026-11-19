"""Provider-neutral chat ingress; no network, credentials, or tool execution."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ChannelKind(StrEnum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEB = "web"
    MCP = "mcp"


@dataclass(frozen=True, slots=True)
class ChannelEnvelope:
    channel: ChannelKind
    event_id: str
    external_user_id: str
    conversation_id: str
    text: str
    received_at: str
    attachment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("event_id", "external_user_id", "conversation_id"):
            value = getattr(self, name)
            if not value or len(value) > 256 or not value.strip():
                raise ValueError(f"{name} must be non-empty and at most 256 characters")
        if len(self.text) > 20_000:
            raise ValueError("text exceeds 20000 characters")
        if len(self.attachment_refs) > 10:
            raise ValueError("at most 10 attachment references are accepted")
        if any(not ref or len(ref) > 1024 for ref in self.attachment_refs):
            raise ValueError("attachment references must be non-empty and at most 1024 characters")
        parsed = datetime.fromisoformat(self.received_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("received_at must include a timezone")


@dataclass(frozen=True, slots=True)
class ChannelIdentityBinding:
    channel: ChannelKind
    external_user_id: str
    principal_id: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ChannelPolicy:
    allowed_channels: frozenset[ChannelKind]
    bindings: tuple[ChannelIdentityBinding, ...]
    max_text_chars: int = 20_000


@dataclass(frozen=True, slots=True)
class IngressDecision:
    accepted: bool
    principal_id: str | None
    reason: str
    event_fingerprint: str


def normalize_envelope(
    *,
    channel: str,
    event_id: str,
    external_user_id: str,
    conversation_id: str,
    text: str,
    received_at: str | None = None,
    attachment_refs: tuple[str, ...] = (),
) -> ChannelEnvelope:
    """Convert adapter fields into a validated, provider-neutral envelope."""
    try:
        kind = ChannelKind(channel.strip().lower())
    except (AttributeError, ValueError) as exc:
        raise ValueError("unsupported channel") from exc
    return ChannelEnvelope(
        channel=kind,
        event_id=event_id,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
        text=text,
        received_at=received_at or datetime.now(UTC).isoformat(),
        attachment_refs=tuple(attachment_refs),
    )


def _fingerprint(envelope: ChannelEnvelope) -> str:
    payload = {
        "channel": envelope.channel.value,
        "event_id": envelope.event_id,
        "external_user_id": envelope.external_user_id,
        "conversation_id": envelope.conversation_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def authorize_ingress(envelope: ChannelEnvelope, policy: ChannelPolicy) -> IngressDecision:
    """Fail-closed identity/channel check; never authorizes downstream actions."""
    fingerprint = _fingerprint(envelope)
    if envelope.channel not in policy.allowed_channels:
        return IngressDecision(False, None, "channel_not_allowed", fingerprint)
    if len(envelope.text) > policy.max_text_chars:
        return IngressDecision(False, None, "message_too_large", fingerprint)
    matches = [
        item
        for item in policy.bindings
        if item.channel is envelope.channel
        and item.external_user_id == envelope.external_user_id
        and item.enabled
    ]
    if len(matches) != 1:
        return IngressDecision(False, None, "identity_unbound_or_ambiguous", fingerprint)
    principal = matches[0].principal_id
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", principal):
        return IngressDecision(False, None, "invalid_principal_binding", fingerprint)
    return IngressDecision(True, principal, "identity_bound_read_only_ingress", fingerprint)
