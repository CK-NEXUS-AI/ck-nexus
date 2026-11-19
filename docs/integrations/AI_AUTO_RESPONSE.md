# CK-NEXUS AI-to-AI Auto-Response

## Purpose

The `creator_app.ai_team.auto_response.AgentMessageBus` provides a bounded,
transport-neutral request/response path between registered CK-NEXUS agents.
A request invokes the recipient's registered handler and returns a response
automatically. Each request and response is recorded in an in-memory audit
history with a shared correlation ID.

## Current integration

`TeamDirector` registers its built-in team members as responders and exposes:

```python
from creator_app.ai_team.team_director import TeamDirector

team = TeamDirector()
response = team.send_agent_message(
    sender="orchestrator",
    recipient="engineer",
    content="Review the API design and list the required tests",
    idempotency_key="design-review-001",
)
print(response.kind, response.content)
```

Use `team.message_bus.broadcast(sender="orchestrator", content="Review this plan")`
to collect automatic responses from available peers. Responses are suggestions;
they are not evidence that code or production operations have succeeded.

## External model providers

The bus is transport-neutral; it does not claim that OpenAI, Gemini, Claude,
Qwen, DeepSeek, or other remote models are connected by default. To connect an
external provider, register a handler that calls the provider adapter using
credentials from the approved secret store. Never put API keys in message
content, metadata, logs, or evidence.

## Guardrails

- The bus rejects self-messaging and unknown recipients.
- Request/response is bounded; it does not recursively dispatch responses.
- Idempotency keys prevent repeating the same request handler within the
  lifetime of a bus instance.
- History is in-memory and bounded by `max_history`; it is not durable storage.
- Provider output is untrusted until independently reviewed and tested.
- Production changes, credential access, external writes, and deployment remain
  governed by CK-NEXUS authorization and execution guardrails.

## Verification

Run:

```bash
.venv/bin/python -m pytest -q creator_app/ai_team/tests/test_auto_response.py creator_app/ai_team/tests/test_team.py
.venv/bin/ruff check creator_app/ai_team/auto_response.py creator_app/ai_team/team_director.py creator_app/ai_team/__init__.py creator_app/ai_team/tests/test_auto_response.py
.venv/bin/ruff format --check creator_app/ai_team/auto_response.py creator_app/ai_team/team_director.py creator_app/ai_team/__init__.py creator_app/ai_team/tests/test_auto_response.py
```
