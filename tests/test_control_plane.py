from creator_app.control_plane.models import ExecutionState
from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator


def test_plan_creates_bounded_development_graph() -> None:
    graph = ControlPlaneOrchestrator().plan("แก้บั๊กระบบ MCP", priority=1)

    assert graph.execution_state is ExecutionState.PLANNED_NOT_EXECUTED
    assert graph.production_status == "NO-GO"
    assert graph.external_mutation_authorized is False
    assert {node.role for node in graph.nodes} >= {
        "research",
        "implementation",
        "verification",
        "security",
    }
    verification = next(node for node in graph.nodes if node.role == "verification")
    implementation = next(node for node in graph.nodes if node.role == "implementation")
    assert implementation.node_id in verification.depends_on


def test_empty_request_is_rejected() -> None:
    try:
        ControlPlaneOrchestrator().plan("   ")
    except ValueError as exc:
        assert str(exc) == "request must not be empty"
    else:
        raise AssertionError("empty request must be rejected")


def test_evidence_bundle_is_snapshotted_when_planning() -> None:
    bundle = {
        "subject_sha": "a" * 40,
        "checks": [{"name": "original", "metadata": {"labels": ["before"]}}],
    }
    graph = ControlPlaneOrchestrator().plan("inspect artifact", evidence_bundle=bundle)
    security = next(node for node in graph.nodes if node.role == "security")

    bundle["checks"][0]["name"] = "mutated"
    bundle["checks"][0]["metadata"]["labels"].append("after")

    assert security.evidence_bundle is not bundle
    assert security.evidence_bundle["checks"][0]["name"] == "original"
    assert security.evidence_bundle["checks"][0]["metadata"]["labels"] == ["before"]
