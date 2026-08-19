"""Tests for the CK-NEXUS development-assistant fabric."""

from creator_app.dev_assistants import ASSISTANTS, AssistantStatus, DevAssistantFabric
from creator_app.dev_assistants.registry import active_assistants, get_assistant


def test_registry_has_expected_active_assistants() -> None:
    ids = {item.assistant_id for item in active_assistants()}
    assert {
        "opencode",
        "gemini_cli",
        "cline",
        "aider",
        "openhands",
        "goose",
        "mini_swe_agent",
        "ollama",
    } <= ids


def test_retired_and_reference_projects_are_not_active() -> None:
    active_ids = {item.assistant_id for item in active_assistants()}
    assert "roo_code" not in active_ids
    assert "continue" not in active_ids
    assert "mcp_reference_servers" not in active_ids
    assert get_assistant("roo_code").status is AssistantStatus.RETIRED


def test_discovery_reports_only_command_names_not_paths() -> None:
    available = {"opencode", "aider"}
    fabric = DevAssistantFabric(
        path_lookup=lambda command: f"/tmp/{command}" if command in available else None
    )
    rows = fabric.discover()
    by_id = {row["assistant_id"]: row for row in rows}
    assert by_id["opencode"]["available"] is True
    assert by_id["opencode"]["command"] == "opencode"
    assert by_id["aider"]["available"] is True
    assert by_id["gemini_cli"]["available"] is False
    assert all(row["external_mutation_authorized"] is False for row in rows)


def test_selection_prefers_capability_match_and_available_tool() -> None:
    fabric = DevAssistantFabric(
        path_lookup=lambda command: command if command == "aider" else None
    )
    rows = fabric.select({"code_edit", "test_fix"}, limit=2)
    assert rows
    assert rows[0]["assistant_id"] == "aider"
    assert rows[0]["available"] is True


def test_selection_can_plan_for_not_yet_installed_tools() -> None:
    fabric = DevAssistantFabric(path_lookup=lambda _command: None)
    rows = fabric.select({"mcp"}, limit=10, require_installed=False)
    ids = {row["assistant_id"] for row in rows}
    assert "gemini_cli" in ids
    assert "cline" in ids
    assert "goose" in ids


def test_parallel_plan_is_non_executing_and_non_release_evidence() -> None:
    fabric = DevAssistantFabric(path_lookup=lambda _command: None)
    plan = fabric.build_parallel_plan(
        "Speed up CK-NEXUS development",
        {
            "implementation": {"code_edit"},
            "issue-fix": {"issue_fix"},
            "offline": {"local_model"},
        },
    )
    assert plan["authority"] == "CK-NEXUS"
    assert plan["production_status"] == "NO-GO"
    assert plan["release_evidence"] is False
    assert plan["external_mutation_authorized"] is False
    assert all(
        stream["execution_state"] == "PLANNED_NOT_EXECUTED"
        for stream in plan["workstreams"]
    )


def test_all_entries_have_upstream_and_license_metadata() -> None:
    for spec in ASSISTANTS:
        assert spec.upstream.startswith("https://github.com/")
        assert spec.license
