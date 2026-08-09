from __future__ import annotations

from pathlib import Path

from scripts import gate_dependency_closure as gate


def _write_pyproject(path: Path) -> None:
    path.write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["alpha>=1"]
[project.optional-dependencies]
gateway = ["beta>=1"]
dev = ["pip-audit>=2"]
billing = []
email = []
github-app = []
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_lock(path: Path, names: list[str]) -> None:
    path.write_text(
        "\n".join(f'[[package]]\nname = "{name}"\nversion = "1.0.0"\n' for name in names),
        encoding="utf-8",
    )


def test_gate_reports_missing_lock_and_runtime(monkeypatch, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    _write_pyproject(pyproject)
    _write_lock(lock, ["alpha", "pip-audit"])
    monkeypatch.setattr(gate, "installed", lambda required: {name: name == "alpha" for name in required})
    monkeypatch.setattr(gate, "registry_status", lambda: gate.RegistryStatus(True, True))

    result = gate.evaluate(pyproject, lock, gate.DEFAULT_GROUPS)

    assert result["ready"] is False
    assert result["missing_lock_packages"] == ["beta"]
    assert result["missing_runtime_modules"] == ["beta", "pip-audit"]


def test_gate_passes_only_when_lock_runtime_and_registry_are_ready(monkeypatch, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    _write_pyproject(pyproject)
    _write_lock(lock, ["alpha", "beta", "pip-audit"])
    monkeypatch.setattr(gate, "installed", lambda required: {name: True for name in required})
    monkeypatch.setattr(gate, "registry_status", lambda: gate.RegistryStatus(True, True))

    result = gate.evaluate(pyproject, lock, gate.DEFAULT_GROUPS)

    assert result["ready"] is True
    assert result["missing_lock_packages"] == []
    assert result["missing_runtime_modules"] == []


def test_registry_status_does_not_expose_url_or_hostname(monkeypatch):
    monkeypatch.setenv("UV_INDEX_URL", "https://user:secret@private.example.invalid/simple")
    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.setattr(gate.socket, "getaddrinfo", lambda *args, **kwargs: [(None,)])

    result = gate.registry_status()

    assert result == gate.RegistryStatus(True, True)
    assert "private.example.invalid" not in repr(result)
    assert "secret" not in repr(result)
