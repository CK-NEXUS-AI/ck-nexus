from __future__ import annotations

import importlib.machinery
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

WRAPPER_PATH = Path(__file__).resolve().parents[1] / "ops/vps/services/cknexus-browser-mcp"


def _load_wrapper():
    loader = importlib.machinery.SourceFileLoader("cknexus_browser_wrapper", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_screenshot_uses_private_capture_and_opened_user_file(tmp_path, monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setenv("SUDO_UID", str(os.getuid()))
    target = tmp_path / "cknexus-browser-mcp-unit-test.png"
    target.touch(mode=0o600)
    target.chmod(0o600)
    observed = {}

    def fake_run(args, **kwargs):
        observed["path"] = Path(args[2])
        observed["kwargs"] = kwargs
        observed["path"].write_bytes(b"verified-png")
        return SimpleNamespace(returncode=0, stdout="captured", stderr="")

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot", str(target)])

    assert wrapper.main() == 0
    assert target.read_bytes() == b"verified-png"
    assert observed["path"].parent != tmp_path
    assert observed["kwargs"]["shell"] is False


def test_screenshot_rejects_symlink_without_running_helper(tmp_path, monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setenv("SUDO_UID", str(os.getuid()))
    victim = tmp_path / "victim.txt"
    victim.write_text("must remain unchanged", encoding="utf-8")
    target = tmp_path / "cknexus-browser-mcp-symlink.png"
    target.symlink_to(victim)
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot", str(target)])

    assert wrapper.main() == 2
    assert victim.read_text(encoding="utf-8") == "must remain unchanged"
