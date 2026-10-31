from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import Mock

MODULE_PATH = Path("scripts/collect_dev_status.py")
SPEC = importlib.util.spec_from_file_location("collect_dev_status", MODULE_PATH)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


def test_collector_command_success_json(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(["gh"], 0, '{"ok": true}', "")
    monkeypatch.setattr(collector.subprocess, "run", Mock(return_value=completed))
    assert collector.command(["gh", "pr", "list", "--json"]) == {"ok": True}


def test_collector_command_timeout_is_not_stale_success(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 20)
    monkeypatch.setattr(collector.subprocess, "run", timeout)
    try:
        collector.command(["gh", "pr", "list"])
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("timeout must propagate")


def test_collector_command_failure_is_not_stale_success(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(["gh"], 1, "", "permission denied")
    monkeypatch.setattr(collector.subprocess, "run", Mock(return_value=completed))
    try:
        collector.command(["gh", "pr", "list"])
    except RuntimeError as exc:
        assert "exited 1" in str(exc)
    else:
        raise AssertionError("non-zero command must fail closed")


def test_collector_redacts_secrets() -> None:
    value = collector.redact({"message": "Authorization: Bearer abc.def",
                              "api_key": "token=secretvalue"})
    assert "abc.def" not in str(value)
    assert "secretvalue" not in str(value)


def test_collect_marks_failed_git_source_as_error(monkeypatch) -> None:
    def fake_command(args, **kwargs):
        if args[:2] == ["git", "rev-parse"]:
            raise subprocess.TimeoutExpired(args, 20)
        if args[:2] == ["gh", "pr"]:
            raise RuntimeError("gh unavailable")
        if args[:2] == ["gh", "issue"] or args[:2] == ["gh", "run"]:
            return []
        if args[0] == "systemctl":
            return ""
        if args[0] == "ss":
            return ""
        if args[0] == "df":
            return "Filesystem Size Used Avail Use% Mounted on"
        return ""

    monkeypatch.setattr(collector, "command", fake_command)
    monkeypatch.setattr(collector, "load_qwen_probe_state", lambda: {
        "value": None, "source": "test", "collected_at": collector.now(), "status": "error"
    })
    payload = collector.collect()
    assert payload["items"]["git"]["status"] == "error"
    assert payload["items"]["git"]["value"] is None
    assert payload["items"]["open_prs"]["status"] == "error"


def test_service_state_preserves_non_active_systemd_states(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(
        ["systemctl", "is-active", "demo.service"], 3, "activating" + chr(10), ""
    )
    monkeypatch.setattr(collector.subprocess, "run", Mock(return_value=completed))
    assert collector.service_state("demo.service") == "activating"
