import pathlib


WEB = pathlib.Path(__file__).resolve().parents[1] / "creator_app" / "web"
HTML = WEB / "cognitive-twin.html"
CSS = WEB / "cognitive-twin.css"
JS = WEB / "cognitive-twin.js"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cognitive_twin_assets_exist() -> None:
    assert HTML.is_file()
    assert CSS.is_file()
    assert JS.is_file()


def test_cognitive_twin_is_thai_first_and_runtime_grounded() -> None:
    html = _read(HTML)
    js = _read(JS)
    assert '<html lang="th"' in html
    assert "ศูนย์ปฏิบัติการ" in html
    assert "แตะตัวละคร" in html
    assert "/api/agnes/status" in js
    assert "/api/agnes/execution/status" in js
    assert "/api/providers/status" in js


def test_cognitive_twin_keeps_authority_and_truth_boundaries_visible() -> None:
    html = _read(HTML)
    assert "CK GOVERNOR" in html
    assert "NO-GO" in html
    assert "OBSERVED" in html
    assert "INFERRED" in html
    assert "SIMULATED" in html
    assert "VERIFIED" in html
    assert "private chain-of-thought" in html


def test_cognitive_twin_has_agent_inspector_and_visual_language() -> None:
    html = _read(HTML)
    js = _read(JS)
    agents = ("agnes", "strategos", "scout", "verifier", "guardian", "builder")
    for agent in agents:
        assert f'data-agent="{agent}"' in html
        assert f"{agent}:" in js
    states = (
        "searching",
        "analyzing",
        "planning",
        "executing",
        "verifying",
        "waiting",
        "blocked",
    )
    for state in states:
        assert state in js
    assert 'data-agent-action="pause" disabled' in html


def test_cognitive_twin_access_token_is_session_scoped_only() -> None:
    js = _read(JS)
    assert 'sessionStorage.getItem("cknexus_access_token")' in js
    assert 'sessionStorage.setItem("cknexus_access_token"' in js
    assert 'localStorage.setItem("cknexus_access_token"' not in js
    assert "raw credentials" in _read(HTML)


def test_cognitive_twin_has_no_external_script_or_style_dependency() -> None:
    html = _read(HTML)
    assert 'src="http://' not in html
    assert 'src="https://' not in html
    assert 'href="http://' not in html
    assert 'href="https://' not in html
    assert '<script src="/static/cognitive-twin.js" defer></script>' in html
    assert '<link rel="stylesheet" href="/static/cognitive-twin.css" />' in html


def test_cognitive_twin_does_not_call_mutating_runtime_endpoints() -> None:
    js = _read(JS)
    forbidden = (
        "/api/agnes/execute",
        "/api/agnes/pipeline/start",
        "/api/agnes/pipeline/",
        "/api/integrations/github-app/token",
        "method: \"POST\"",
        "method: 'POST'",
    )
    for value in forbidden:
        assert value not in js


def test_cognitive_twin_accessibility_and_motion_controls_exist() -> None:
    html = _read(HTML)
    css = _read(CSS)
    assert "prefers-reduced-motion" in css
    assert 'id="high-contrast"' in html
    assert 'id="motion-quality"' in html
    assert 'id="font-scale"' in html
    assert 'id="background-pause"' in html
