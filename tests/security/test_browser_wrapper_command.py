import importlib.util
import io
from importlib.machinery import SourceFileLoader
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[2] / "ops" / "vps" / "services" / "cknexus-browser-mcp"
LOADER = SourceFileLoader("cknexus_browser_wrapper_test", str(WRAPPER))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
MODULE = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(MODULE)


def test_open_url_is_sent_on_stdin_not_command_arguments(monkeypatch):
    captured = {}

    class Result:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs.get("input")
        return Result()

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(MODULE.sys, "argv", [str(WRAPPER), "open"])
    monkeypatch.setattr(MODULE.sys, "stdin", io.StringIO("https://github.com/example/repo\n"))

    assert MODULE.main() == 0
    assert captured["args"] == [MODULE.HELPER, "open"]
    assert captured["input"] == "https://github.com/example/repo\n"


def test_open_rejects_unapproved_url_before_subprocess(monkeypatch):
    monkeypatch.setattr(MODULE.sys, "argv", [str(WRAPPER), "open"])
    monkeypatch.setattr(MODULE.sys, "stdin", io.StringIO("https://evil.example/\n"))
    monkeypatch.setattr(
        MODULE.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )
    assert MODULE.main() == 2


def test_screenshot_path_is_sent_on_stdin_and_validated(monkeypatch):
    captured = {}

    class Result:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs.get("input")
        return Result()

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(MODULE.sys, "argv", [str(WRAPPER), "screenshot"])
    monkeypatch.setattr(MODULE.sys, "stdin", io.StringIO("/tmp/cknexus-browser-mcp-123.png\n"))

    assert MODULE.main() == 0
    assert captured["args"] == [MODULE.HELPER, "screenshot"]
    assert captured["input"] == "/tmp/cknexus-browser-mcp-123.png\n"
