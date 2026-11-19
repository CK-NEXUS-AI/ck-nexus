from __future__ import annotations

import sys
import types

import pytest

from orchestration.adk_graph import (
    AdkGraphUnavailable,
    build_sequential_workflow,
)


def test_empty_graph_is_rejected():
    with pytest.raises(ValueError, match="at least one node"):
        build_sequential_workflow("demo", [])


def test_empty_name_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        build_sequential_workflow(" ", [object()])


def test_adapter_uses_adk_workflow_and_start_edge(monkeypatch):
    captured = {}

    class FakeWorkflow:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_adk = types.ModuleType("google.adk")
    fake_adk.Workflow = FakeWorkflow
    fake_google = types.ModuleType("google")
    fake_google.adk = fake_adk

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.adk", fake_adk)

    n1 = object()
    n2 = object()
    result = build_sequential_workflow("approved-flow", [n1, n2])

    assert isinstance(result, FakeWorkflow)
    assert captured["name"] == "approved-flow"
    assert captured["edges"] == [("START", n1, n2)]


def test_missing_adk_has_explicit_failure(monkeypatch):
    real_import = __import__

    def blocked_import(name, *args, **kwargs):
        if name == "google.adk":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked_import)
    with pytest.raises(AdkGraphUnavailable, match="google-adk is not installed"):
        build_sequential_workflow("demo", [object()])
