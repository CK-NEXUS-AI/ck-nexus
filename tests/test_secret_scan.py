from scripts.secret_scan import PATTERNS


def test_openai_key_pattern_detects_token_at_value_boundary():
    token = "sk-" + "a" * 24
    assert PATTERNS["openai_key"].search(f"OPENAI_API_KEY={token}")


def test_openai_key_pattern_detects_project_token():
    token = "sk-proj-" + "b" * 24
    assert PATTERNS["openai_key"].search(f'"{token}"')


def test_openai_key_pattern_does_not_match_task_queue_slug():
    text = (
        "Design document created at "
        "docs/specs/2026-10-22-mcp-task-queue-integration-design.md"
    )
    assert not PATTERNS["openai_key"].search(text)
