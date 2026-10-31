from scripts.secret_scan import PATTERNS


def test_openai_key_pattern_does_not_match_task_queue_words() -> None:
    assert PATTERNS["openai_key"].search("mcp-task-queue-interface") is None


def test_openai_key_pattern_matches_key_shaped_value() -> None:
    key_prefix = "s" + "k-" + "proj-"
    candidate = "OPENAI_KEY=" + key_prefix + ("a" * 32)
    assert PATTERNS["openai_key"].search(candidate)
