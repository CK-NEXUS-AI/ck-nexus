from __future__ import annotations

import importlib.util

from scripts import gate_trusted_toolchain as gate


def test_installed_modules_uses_import_names(monkeypatch):
    seen: list[str] = []

    def fake_find_spec(name: str):
        seen.append(name)
        return object() if name == "present_mod" else None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    result = gate.installed_modules({"present": "present_mod", "missing": "missing_mod"})
    assert result == {"present": True, "missing": False}
    assert seen == ["present_mod", "missing_mod"]


def test_registry_probe_never_returns_credentials(monkeypatch):
    monkeypatch.setenv("UV_INDEX_URL", "https://user:super-secret@example.invalid/simple")
    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.setattr(gate.socket, "getaddrinfo", lambda *args, **kwargs: [(None,)])

    result = gate._registry_host()

    assert result.configured is True
    assert result.host == "example.invalid"
    assert result.dns_resolves is True
    assert "user" not in repr(result)
    assert "super-secret" not in repr(result)
