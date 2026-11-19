from __future__ import annotations

import pytest

from creator_app.ai_team.auto_response import AgentMessageBus, AgentMessageError
from creator_app.ai_team.team_director import TeamDirector


def test_request_gets_automatic_response_and_audit_history():
    bus = AgentMessageBus()
    bus.register("reviewer", lambda message: f"reviewed: {message.content}")

    response = bus.request(sender="orchestrator", recipient="reviewer", content="check tests")

    assert response.kind == "response"
    assert response.sender == "reviewer"
    assert response.recipient == "orchestrator"
    assert response.content == "reviewed: check tests"
    assert len(bus.history()) == 2
    assert bus.history()[0].kind == "request"
    assert bus.history()[1].metadata["in_reply_to"] == bus.history()[0].message_id


def test_idempotency_returns_original_response_without_recalling_handler():
    calls = []
    bus = AgentMessageBus()
    bus.register("worker", lambda message: calls.append(message.content) or "done")

    first = bus.request(
        sender="orchestrator",
        recipient="worker",
        content="run check",
        idempotency_key="task-1",
    )
    second = bus.request(
        sender="orchestrator",
        recipient="worker",
        content="run check again",
        idempotency_key="task-1",
    )

    assert first == second
    assert calls == ["run check"]


def test_self_message_and_missing_recipient_are_rejected():
    bus = AgentMessageBus()
    bus.register("worker", lambda message: "ok")

    with pytest.raises(AgentMessageError, match="self_messaging"):
        bus.request(sender="worker", recipient="worker", content="hello")
    with pytest.raises(AgentMessageError, match="recipient_unavailable"):
        bus.request(sender="orchestrator", recipient="missing", content="hello")


def test_broadcast_collects_automatic_peer_responses():
    bus = AgentMessageBus()
    bus.register("qa", lambda message: "tests look good")
    bus.register("security", lambda message: "no critical findings")

    replies = bus.broadcast(sender="orchestrator", content="review release")

    assert [reply.content for reply in replies] == [
        "tests look good",
        "no critical findings",
    ]
    assert all(reply.kind == "response" for reply in replies)


def test_team_director_exposes_agent_to_agent_auto_response():
    team = TeamDirector()
    response = team.send_agent_message(
        sender="orchestrator",
        recipient="engineer",
        content="Build a small API and explain its tests",
        idempotency_key="auto-response-test",
    )

    assert response.kind == "response"
    assert response.sender == "engineer"
    assert response.content
    assert team.message_bus.status()["message_count"] == 2


def test_idempotency_key_is_scoped_to_sender_and_recipient():
    calls = []
    bus = AgentMessageBus()
    bus.register(
        "worker", lambda message: calls.append(message.sender) or f"hello {message.sender}"
    )

    first = bus.request(
        sender="orchestrator-a",
        recipient="worker",
        content="status",
        idempotency_key="same-key",
    )
    second = bus.request(
        sender="orchestrator-b",
        recipient="worker",
        content="status",
        idempotency_key="same-key",
    )

    assert first.content == "hello orchestrator-a"
    assert second.content == "hello orchestrator-b"
    assert calls == ["orchestrator-a", "orchestrator-b"]
