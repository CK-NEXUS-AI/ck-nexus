from __future__ import annotations

from scripts.secret_scan import PATTERNS


def test_openai_key_scanner_does_not_treat_mcp_task_queue_path_as_secret():
    text = "docs/specs/2026-10-22-mcp-task-queue-interface-with-durable-state.md"

    assert PATTERNS["openai_key"].search(text) is None


def test_openai_key_scanner_still_detects_project_key_shape():
    token = "sk-proj-" + "a" * 36
    text = f'OPENAI_API_KEY="{token}"'

    assert PATTERNS["openai_key"].search(text) is not None
