from pathlib import Path


def test_signup_feedback_uses_text_nodes_for_dynamic_values() -> None:
    for filename in ("creator_app/web/signup.js", "creator_app/web/static/signup.js"):
        source = Path(filename).read_text(encoding="utf-8")
        assert "${data.error}" not in source
        assert "${d.error}" not in source
        assert "result.textContent" in source or "msg.textContent" in source
