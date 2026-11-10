from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "creator_app/web/signup.html"
SCRIPT = ROOT / "creator_app/web/static/signup.js"


def test_signup_does_not_expose_nonexistent_provider_key_write_route():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    assert "keyInput" not in html
    assert "ADD KEY" not in html
    assert "function addKey" not in script
    assert "/set-key" not in script
    assert "populateSelect" not in script
