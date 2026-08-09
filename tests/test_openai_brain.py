from __future__ import annotations

import sys
from types import SimpleNamespace

from creator_app.openai_brain import build_openai_agents_run_config


def test_openai_brain_uses_per_run_provider_without_global_key(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured["provider"] = kwargs

    class FakeRunConfig:
        def __init__(self, **kwargs):
            captured["run"] = kwargs

    monkeypatch.setitem(
        sys.modules,
        "agents",
        SimpleNamespace(OpenAIProvider=FakeProvider, RunConfig=FakeRunConfig),
    )

    built = build_openai_agents_run_config(
        api_key="sk-test-only-secret",
        model="gpt-test",
        workflow_name="CK Test",
        group_id="session-1",
    )

    assert captured["provider"] == {"api_key": "sk-test-only-secret", "use_responses": True}
    run = captured["run"]
    assert run["model"] == "gpt-test"
    assert run["model_provider"] is built.provider
    assert run["trace_include_sensitive_data"] is False
    assert run["tracing_disabled"] is True
    assert run["group_id"] == "session-1"
    assert "tracing" not in run
    assert "sk-test-only-secret" not in repr(built)


def test_openai_brain_scopes_tracing_key_to_run(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            pass

    class FakeRunConfig:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "agents",
        SimpleNamespace(OpenAIProvider=FakeProvider, RunConfig=FakeRunConfig),
    )

    build_openai_agents_run_config(
        api_key="sk-trace-test",
        model="gpt-test",
        workflow_name="CK Trace Test",
        tracing_enabled=True,
    )

    assert captured["tracing_disabled"] is False
    assert captured["tracing"] == {"api_key": "sk-trace-test"}
