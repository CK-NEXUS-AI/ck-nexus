import re
from pathlib import Path


def test_signup_validate_all_uses_text_nodes_for_dynamic_values() -> None:
    cases = (
        ("creator_app/web/signup.js", "function exportConfig()"),
        ("creator_app/web/static/signup.js", "function exportJSON()"),
    )
    for filename, next_function in cases:
        source = Path(filename).read_text(encoding="utf-8")
        start = source.index("async function validateAll() {")
        end = source.index(next_function, start)
        body = source[start:end]

        assert "innerHTML" not in body
        assert "document.createElement" in body
        assert "icon.textContent = String(result.icon ?? '')" in body
        assert "name.textContent = String(result.name ?? '')" in body
        assert "badge.textContent = result.valid ?" in body
        assert "list.append(item)" in body
        assert re.search(r"\$\{[^}]*\.(error|name|icon)", body) is None
