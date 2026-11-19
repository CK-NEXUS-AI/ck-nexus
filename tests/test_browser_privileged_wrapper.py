from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve().parents[1] / "ops/vps/services/cknexus-browser-mcp"


def _load_wrapper():
    loader = importlib.machinery.SourceFileLoader("cknexus_browser_wrapper", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_privileged_screenshot_wrapper_rejects_non_temp_path(monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(
        wrapper.sys,
        "argv",
        [str(WRAPPER_PATH), "screenshot", "/etc/cron.d/cknexus.png"],
    )
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert wrapper.main() == 2


def test_privileged_screenshot_wrapper_rejects_unexpected_filename(monkeypatch, tmp_path):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.tempfile, "gettempdir", lambda: str(tmp_path))
    target = tmp_path / "not-an-approved-name.png"
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot", str(target)])
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert wrapper.main() == 2
