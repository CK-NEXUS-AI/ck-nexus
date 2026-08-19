"""Cross-channel conversation identity and deduplication contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelSession:
    channel: str
    channel_session_id: str
    conversation_id: str
    tenant_id: str
    user_id: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.channel,
                self.channel_session_id,
                self.conversation_id,
                self.tenant_id,
                self.user_id,
            )
        ):
            raise ValueError("channel-session identity fields must not be empty")


class ConversationContinuityRegistry:
    """Bind channel sessions to one conversation without copying raw channel history."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], ChannelSession] = {}
        self._source_digests: dict[str, set[str]] = {}

    def bind(self, session: ChannelSession) -> None:
        key = (session.channel, session.channel_session_id)
        existing = self._sessions.get(key)
        if existing is not None and existing != session:
            raise ValueError("channel session is already bound to another conversation")
        self._sessions[key] = session

    def resolve(self, channel: str, channel_session_id: str) -> ChannelSession | None:
        return self._sessions.get((channel, channel_session_id))

    def seen_source(self, conversation_id: str, source_identity: str, content: str) -> bool:
        digest = hashlib.sha256(f"{source_identity}\0{content}".encode()).hexdigest()
        bucket = self._source_digests.setdefault(conversation_id, set())
        if digest in bucket:
            return True
        bucket.add(digest)
        return False


def conversation_id_for(*, tenant_id: str, user_id: str, seed: str) -> str:
    material = f"{tenant_id}:{user_id}:{seed}".encode()
    return f"conv-{hashlib.sha256(material).hexdigest()[:20]}"
