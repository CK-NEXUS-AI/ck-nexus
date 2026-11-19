"""Bounded AI-to-AI request/response messaging for CK-NEXUS.

This is a transport-neutral coordination layer. Provider/API adapters can be
registered as handlers; this module never assumes a model is connected.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

MessageHandler = Callable[["AgentMessage"], str | None]


@dataclass(frozen=True, slots=True)
class AgentMessage:
    message_id: str
    conversation_id: str
    correlation_id: str
    sender: str
    recipient: str
    kind: str
    content: str
    hop_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class AgentMessageError(RuntimeError):
    """Raised when a message cannot be safely delivered."""


class AgentMessageBus:
    """Synchronous request/response bus with bounded hops and audit history.

    Handlers are local callbacks. Connect real model APIs by registering an
    adapter callback; API credentials must remain inside that adapter.
    """

    def __init__(self, *, max_hops: int = 4, max_history: int = 500) -> None:
        if not 1 <= max_hops <= 20:
            raise ValueError("max_hops must be between 1 and 20")
        if max_history < 1:
            raise ValueError("max_history must be positive")
        self.max_hops = max_hops
        self.max_history = max_history
        self._handlers: dict[str, MessageHandler] = {}
        self._history: list[AgentMessage] = []
        self._seen_requests: dict[tuple[str, str, str], AgentMessage] = {}

    def register(self, agent_id: str, handler: MessageHandler) -> None:
        agent_id = agent_id.strip()
        if not agent_id:
            raise ValueError("agent_id_required")
        if not callable(handler):
            raise TypeError("handler_must_be_callable")
        self._handlers[agent_id] = handler

    def unregister(self, agent_id: str) -> bool:
        return self._handlers.pop(agent_id, None) is not None

    def request(
        self,
        *,
        sender: str,
        recipient: str,
        content: str,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AgentMessage:
        """Deliver a request and automatically return the recipient's response."""
        if not sender.strip() or not recipient.strip():
            raise ValueError("sender_and_recipient_required")
        if sender == recipient:
            raise AgentMessageError("self_messaging_not_allowed")
        if not content.strip():
            raise ValueError("message_content_required")
        if recipient not in self._handlers:
            raise AgentMessageError(f"recipient_unavailable:{recipient}")
        cache_key = (sender, recipient, idempotency_key) if idempotency_key else None
        if cache_key is not None and cache_key in self._seen_requests:
            return self._seen_requests[cache_key]
        request_id = correlation_id or f"corr-{uuid4().hex}"
        conversation = conversation_id or f"conv-{uuid4().hex}"
        request = AgentMessage(
            message_id=f"msg-{uuid4().hex}",
            conversation_id=conversation,
            correlation_id=request_id,
            sender=sender,
            recipient=recipient,
            kind="request",
            content=content,
            hop_count=0,
            metadata=dict(metadata or {}),
        )
        self._record(request)
        try:
            response_text = self._handlers[recipient](request)
        except Exception as exc:
            response_text = None
            error = f"handler_error:{type(exc).__name__}"
        else:
            error = "handler_returned_no_response"
        response = AgentMessage(
            message_id=f"msg-{uuid4().hex}",
            conversation_id=conversation,
            correlation_id=request_id,
            sender=recipient,
            recipient=sender,
            kind="response" if response_text is not None else "error",
            content=str(response_text) if response_text is not None else error,
            hop_count=1,
            metadata={"in_reply_to": request.message_id},
        )
        self._record(response)
        if cache_key is not None:
            self._seen_requests[cache_key] = response
        return response

    def broadcast(
        self,
        *,
        sender: str,
        content: str,
        recipients: tuple[str, ...] | None = None,
        correlation_id: str | None = None,
    ) -> tuple[AgentMessage, ...]:
        """Ask each selected peer for an automatic response, within hop budget."""
        if self.max_hops < 1:
            return ()
        selected = tuple(recipients) if recipients is not None else tuple(self._handlers)
        replies: list[AgentMessage] = []
        for recipient in selected:
            if recipient == sender or recipient not in self._handlers:
                continue
            replies.append(
                self.request(
                    sender=sender,
                    recipient=recipient,
                    content=content,
                    correlation_id=correlation_id,
                )
            )
        return tuple(replies)

    def history(self, *, conversation_id: str | None = None) -> tuple[AgentMessage, ...]:
        """Return an immutable snapshot of message history."""
        if conversation_id is None:
            return tuple(self._history)
        return tuple(m for m in self._history if m.conversation_id == conversation_id)

    def status(self) -> dict[str, object]:
        return {
            "registered_agents": sorted(self._handlers),
            "agent_count": len(self._handlers),
            "message_count": len(self._history),
            "max_hops": self.max_hops,
            "max_history": self.max_history,
        }

    def _record(self, message: AgentMessage) -> None:
        self._history.append(message)
        overflow = len(self._history) - self.max_history
        if overflow > 0:
            del self._history[:overflow]
