from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from creator_app import cli


def test_install_prepares_state_directory(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path / "state"))
    usage = type("Usage", (), {"free": cli.MIN_FREE_BYTES})()
    monkeypatch.setattr(cli.shutil, "disk_usage", lambda _path: usage)
    assert cli.install() == 0
    assert (tmp_path / "state" / "logs").is_dir()
    assert "Installation ready" in capsys.readouterr().out


def test_install_fails_closed_on_low_disk(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(cli.shutil, "disk_usage", lambda _path: type("U", (), {"free": 1})())
    assert cli.install() == 2


def test_start_reuses_running_pid(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path))
    (tmp_path / "runtime.pid").write_text("123", encoding="utf-8")
    monkeypatch.setattr(cli, "_process_alive", lambda _pid: True)
    assert cli.start() == 0
    assert "already running" in capsys.readouterr().out


def test_start_writes_pid_and_uses_uvicorn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(cli.time, "sleep", lambda _value: None)
    calls: list[list[str]] = []

    class FakeProcess:
        pid = 456

        def poll(self):
            return None

    def fake_popen(command, **_kwargs):
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    assert cli.start(host="127.0.0.1", port=8123) == 0
    assert calls[0][-4:] == ["--host", "127.0.0.1", "--port", "8123"]
    assert (tmp_path / "runtime.pid").read_text(encoding="utf-8") == "456"


def test_status_reports_stopped_and_removes_stale_pid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path))
    (tmp_path / "runtime.pid").write_text("789", encoding="utf-8")
    monkeypatch.setattr(cli, "_process_alive", lambda _pid: False)
    assert cli.status() == 1
    assert not (tmp_path / "runtime.pid").exists()


def test_stop_sends_sigterm_and_removes_pid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_STATE_DIR", str(tmp_path))
    (tmp_path / "runtime.pid").write_text("321", encoding="utf-8")
    states = iter([True, False])
    monkeypatch.setattr(cli, "_process_alive", lambda _pid: next(states))
    monkeypatch.setattr(cli.time, "sleep", lambda _value: None)
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(cli.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    assert cli.stop() == 0
    assert sent and sent[0][0] == 321
    assert not (tmp_path / "runtime.pid").exists()


def test_help_subcommand_returns_zero(capsys) -> None:
    assert cli.main(["help"]) == 0
    assert "CK-NEXUS simple runtime control" in capsys.readouterr().out


def test_no_argument_preserves_legacy_start(monkeypatch) -> None:
    called = []
    fake_main = SimpleNamespace(main=lambda: called.append(True))
    monkeypatch.setitem(__import__("sys").modules, "main", fake_main)
    assert cli.main([]) is None
    assert called == [True]
