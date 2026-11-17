from __future__ import annotations

import creator_app.agnes.mcp_server as mcp_server


def test_browser_open_rejects_non_https_and_unapproved_hosts():
    assert (
        mcp_server.cknexus_browser_open("http://github.com")["error_code"] == "BROWSER_URL_DENIED"
    )
    assert (
        mcp_server.cknexus_browser_open("https://example.org")["error_code"] == "BROWSER_URL_DENIED"
    )


def test_browser_open_rejects_localhost_and_url_credentials():
    assert (
        mcp_server.cknexus_browser_open("https://127.0.0.1:9222/json")["error_code"]
        == "BROWSER_URL_DENIED"
    )
    assert (
        mcp_server.cknexus_browser_open("https://user:pass@github.com")["error_code"]
        == "BROWSER_URL_DENIED"
    )


def test_browser_tools_are_read_only_and_report_safe_metadata(monkeypatch):
    class Result:
        returncode = 0
        stdout = '{"ok":true,"browser":"Chrome/142","pages":[]}'
        stderr = ""

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr(mcp_server.subprocess, "run", fake_run)
    result = mcp_server.cknexus_browser_status()
    assert result["ok"] is True
    assert calls[0][-1] == "status"
    assert not any(x in calls[0] for x in ("click", "type", "submit", "delete"))


def test_browser_open_dispatches_only_approved_https_navigation(monkeypatch):
    class Result:
        returncode = 0
        stdout = '{"ok":true,"url":"https://github.com/CK-NEXUS-AI/ck-nexus","title":"CK-NEXUS"}'
        stderr = ""

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr(mcp_server.subprocess, "run", fake_run)
    result = mcp_server.cknexus_browser_open("https://github.com/CK-NEXUS-AI/ck-nexus")
    assert result["ok"] is True
    assert result["external_mutation_authorized"] is False
    assert calls[0][0:3] == ["sudo", "-n", "/usr/local/sbin/cknexus-browser-mcp"]
    assert calls[0][-2:] == ["open", "https://github.com/CK-NEXUS-AI/ck-nexus"]


def test_screenshot_delegates_private_temp_path_creation_to_wrapper(monkeypatch):
    observed = {}

    def screenshot(action, argument=None):
        observed["action"] = action
        observed["argument"] = argument
        return {"ok": True, "result": "captured"}

    monkeypatch.setattr(mcp_server, "_run_browser_tool", screenshot)
    result = mcp_server.cknexus_browser_screenshot()

    assert result["ok"] is True
    assert observed == {"action": "screenshot", "argument": None}
