from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator
from creator_app.dev_assistants.orchestrator import DevAssistantFabric


def test_control_plane_routes_only_to_installed_capable_assistants() -> None:
    fabric = DevAssistantFabric(
        path_lookup=lambda command: (
            f"/usr/bin/{command}" if command in {"opencode", "gemini"} else None
        )
    )
    graph = ControlPlaneOrchestrator(fabric=fabric).plan("inspect and improve MCP routing")

    discovered = {item["assistant_id"]: item for item in fabric.discover()}
    assert graph.nodes
    for node in graph.nodes:
        for assistant_id in node.candidates:
            assert discovered[assistant_id]["available"] is True
            assert set(node.required_capabilities) & set(discovered[assistant_id]["capabilities"])


def test_control_plane_uses_registry_capabilities_not_undefined_role_tags() -> None:
    graph = ControlPlaneOrchestrator().plan("fix a bug")
    expected = {
        "research": {"repo_analysis", "web"},
        "implementation": {"code_edit"},
        "verification": {"test_fix"},
        "security": {"sandbox"},
    }
    for node in graph.nodes:
        assert set(node.required_capabilities) == expected[node.role]


def test_installed_codex_and_claude_are_discoverable_routing_workers() -> None:
    from creator_app.dev_assistants.registry import active_assistants

    registered = {item.assistant_id: item for item in active_assistants()}
    assert {"codex", "claude_code"} <= set(registered)
    assert "code_edit" in registered["codex"].capabilities
    assert "code_edit" in registered["claude_code"].capabilities

    fabric = DevAssistantFabric(
        path_lookup=lambda command: (
            f"/usr/bin/{command}" if command in {"codex", "claude"} else None
        )
    )
    graph = ControlPlaneOrchestrator(fabric=fabric).plan("implement a small bug fix")
    implementation = next(node for node in graph.nodes if node.role == "implementation")
    assert {"codex", "claude_code"} <= set(implementation.candidates)
