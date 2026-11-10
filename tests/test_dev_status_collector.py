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
    value = collector.redact(
        {"message": "Authorization: Bearer abc.def", "api_key": "token=secretvalue"}
    )
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
    monkeypatch.setattr(
        collector,
        "load_qwen_probe_state",
        lambda: {
            "value": None,
            "source": "test",
            "collected_at": collector.now(),
            "status": "error",
        },
    )
    payload = collector.collect()
    assert payload["items"]["git"]["status"] == "error"
    assert payload["items"]["git"]["value"] is None
    assert payload["items"]["open_prs"]["status"] == "error"
    assert payload["items"]["mcp"]["status"] == "error"


def test_service_state_preserves_non_active_systemd_states(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(
        ["systemctl", "is-active", "demo.service"], 3, "activating" + chr(10), ""
    )
    monkeypatch.setattr(collector.subprocess, "run", Mock(return_value=completed))
    assert collector.service_state("demo.service") == "activating"


def test_qwen_probe_does_not_cache_missing_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(collector, "OUTPUT", tmp_path / "dev_status.json")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_MODEL", "qwen-test")
    result = collector.probe_qwen_daily()
    assert result["status"] == "error"
    assert not (tmp_path / "qwen_probe_state.json").exists()


def test_qwen_probe_rejects_unapproved_base_url_without_sending_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(collector, "OUTPUT", tmp_path / "dev_status.json")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret-never-used")
    monkeypatch.setenv("QWEN_MODEL", "qwen-test")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "http://attacker.invalid/compatible-mode/v1")
    result = collector.probe_qwen_daily()
    assert result["status"] == "error"
    assert "test-secret-never-used" not in str(result)
    assert not (tmp_path / "qwen_probe_state.json").exists()


def test_cached_qwen_failure_is_not_reported_as_ok(tmp_path, monkeypatch) -> None:
    import json
    from datetime import UTC, datetime

    monkeypatch.setattr(collector, "OUTPUT", tmp_path / "dev_status.json")
    state = {
        "date": datetime.now(UTC).date().isoformat(),
        "collected_at": collector.now(),
        "result": {"last_success": None, "last_failure": collector.now()},
    }
    (tmp_path / "qwen_probe_state.json").write_text(json.dumps(state), encoding="utf-8")
    assert collector.load_qwen_probe_state()["status"] == "error"


def test_collect_does_not_use_non_readonly_github_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls = []

    def fake_command(args, **kwargs):
        calls.append(args)
        if args[:2] == ["git", "rev-parse"]:
            return "abc123"
        if args[:2] == ["git", "branch"]:
            return "main"
        if args[:2] == ["git", "status"]:
            return ""
        if args[0] == "systemctl":
            return ""
        if args[0] == "ss":
            return "LISTEN 127.0.0.1:8765"
        if args[0] == "df":
            return "Filesystem Size Used Avail Use% Mounted on"
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(collector, "command", fake_command)
    monkeypatch.setattr(
        collector,
        "load_qwen_probe_state",
        lambda: {
            "value": None,
            "source": "test",
            "collected_at": collector.now(),
            "status": "error",
        },
    )
    payload = collector.collect()
    for key in ("open_prs", "open_issues", "main_ci"):
        assert payload["items"][key]["status"] == "error"
        assert "no read-only GitHub token configured" in payload["items"][key]["error"]
    assert not any(args[:2] == ["gh", "pr"] for args in calls)
    assert not any(args[:2] == ["gh", "issue"] for args in calls)
    assert not any(args[:2] == ["gh", "run"] for args in calls)


def test_qwen_probe_uses_peer_bound_transport_and_redacts_credential(tmp_path, monkeypatch) -> None:
    import json

    monkeypatch.setattr(collector, "OUTPUT", tmp_path / "dev_status.json")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-secret-never-persist")
    monkeypatch.setenv("QWEN_MODEL", "qwen-test")
    monkeypatch.setenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    calls = []

    class Response:
        status = 200
        body = b'{"choices":[{"message":{"content":"OK"}}]}'

    class FakeTransport:
        def __init__(self, *, max_response_bytes):
            assert max_response_bytes == 65536

        def request(self, method, url, *, headers, body, timeout):
            calls.append((method, url, headers, body, timeout))
            return Response()

    monkeypatch.setattr(collector, "UrllibHttpTransport", FakeTransport)
    result = collector.probe_qwen_daily()

    assert result["status"] == "ok"
    assert len(calls) == 1
    method, url, headers, body, timeout = calls[0]
    assert method == "POST"
    assert url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert headers["Authorization"] == "Bearer test-secret-never-persist"
    assert json.loads(body)["model"] == "qwen-test"
    assert timeout == 15
    state = (tmp_path / "qwen_probe_state.json").read_text(encoding="utf-8")
    assert "test-secret-never-persist" not in state
