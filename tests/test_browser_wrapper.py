from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = ROOT / "ops/vps/services/cknexus-browser-mcp"


def _load_wrapper():
    loader = SourceFileLoader("cknexus_browser_wrapper", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_screenshot_uses_private_wrapper_owned_temp_path(tmp_path, monkeypatch, capsys):
    wrapper = _load_wrapper()
    screenshot_dir = tmp_path / "cknexus-browser-test"
    screenshot_dir.mkdir(mode=0o700)
    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", lambda prefix: str(screenshot_dir))
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot"])
    monkeypatch.setenv("SUDO_UID", "1000")
    monkeypatch.setenv("SUDO_GID", "1000")
    chown_calls = []
    monkeypatch.setattr(wrapper.os, "chown", lambda *args: chown_calls.append(args))
    observed = {}

    class Result:
        returncode = 0
        stdout = '{"ok":true,"path":"captured"}'
        stderr = ""

    def fake_run(args, **_kwargs):
        observed["args"] = args
        Path(args[-1]).write_bytes(b"png")
        return Result()

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)

    assert wrapper.main() == 0
    screenshot_path = Path(observed["args"][-1])
    assert screenshot_path.parent == screenshot_dir
    assert screenshot_path.read_bytes() == b"png"
    assert screenshot_path.stat().st_mode & 0o777 == 0o600
    assert screenshot_dir.stat().st_mode & 0o777 == 0o700
    assert chown_calls == [
        (str(screenshot_path), 1000, 1000),
        (str(screenshot_dir), 1000, 1000),
    ]
    assert '"path":"captured"' in capsys.readouterr().out


def test_screenshot_requires_authenticated_sudo_caller(monkeypatch, capsys):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot"])
    monkeypatch.delenv("SUDO_UID", raising=False)
    monkeypatch.delenv("SUDO_GID", raising=False)
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )

    assert wrapper.main() == 2
    assert "authenticated sudo caller" in capsys.readouterr().err


def test_screenshot_retention_is_bounded_per_caller(tmp_path, monkeypatch):
    import os
    import time

    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.tempfile, "gettempdir", lambda: str(tmp_path))
    now = time.time()
    for index in range(12):
        directory = tmp_path / f"cknexus-browser-{index}"
        directory.mkdir()
        (directory / "screenshot.png").write_bytes(b"png")
        modified = now - index * 60
        os.utime(directory, (modified, modified))
    unrelated = tmp_path / "other-browser-result"
    unrelated.mkdir()
    (unrelated / "screenshot.png").write_bytes(b"keep")

    wrapper.cleanup_screenshot_artifacts(os.getuid())

    retained = list(tmp_path.glob("cknexus-browser-*"))
    assert len(retained) == 10
    assert not (tmp_path / "cknexus-browser-10").exists()
    assert not (tmp_path / "cknexus-browser-11").exists()
    assert unrelated.exists()
