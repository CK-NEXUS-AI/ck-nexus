from __future__ import annotations

import base64
import importlib.machinery
import importlib.util
import json
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve().parents[1] / "ops/vps/services/cknexus-browser-mcp"


def _load_wrapper():
    loader = importlib.machinery.SourceFileLoader("cknexus_browser_wrapper", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_privileged_screenshot_wrapper_rejects_caller_supplied_path(monkeypatch):
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


def test_privileged_screenshot_wrapper_rejects_extra_path_argument(monkeypatch, tmp_path):
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


def test_privileged_screenshot_uses_private_generated_path_and_returns_image(
    monkeypatch, tmp_path, capsys
):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper, "PRIVATE_TMP_ROOT", str(tmp_path))
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot"])
    observed = {}

    class Result:
        returncode = 0
        stdout = '{"ok":true}'
        stderr = ""

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        output = Path(args[-1])
        assert output.parent.parent == tmp_path
        assert output.parent.stat().st_mode & 0o777 == 0o700
        output.write_bytes(b"png-data")
        return Result()

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    assert wrapper.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["screenshot_base64"] == base64.b64encode(b"png-data").decode("ascii")
    assert payload["screenshot_mime_type"] == "image/png"
    assert observed["args"][0:2] == [wrapper.HELPER, "screenshot"]
    assert observed["kwargs"]["shell"] is False
    assert not Path(observed["args"][-1]).exists()


def test_privileged_screenshot_rejects_caller_supplied_path(monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper.sys, "argv", [str(WRAPPER_PATH), "screenshot", "/tmp/attacker.png"])
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    assert wrapper.main() == 2
