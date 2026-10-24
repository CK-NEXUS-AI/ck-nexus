from scripts.secret_scan import PATTERNS


def test_openai_key_pattern_does_not_match_task_queue_words() -> None:
    assert PATTERNS["openai_key"].search("mcp-task-queue-interface") is None


def test_openai_key_pattern_matches_key_shaped_value() -> None:
    assert PATTERNS["openai_key"].search("OPENAI_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz012345")
