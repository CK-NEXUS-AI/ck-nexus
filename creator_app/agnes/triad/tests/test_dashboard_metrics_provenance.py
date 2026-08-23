from creator_app.agnes.triad import (
    CandidateArtifact,
    ClaimState,
    ProvenanceGraph,
    ProvenanceNode,
    TriadDashboardProjector,
    TriadEvent,
    TriadEventBus,
    TriadEventType,
    TriadMetrics,
    TriadRole,
)


def test_metrics_penalize_repetition_and_high_risk() -> None:
    good = TriadMetrics(new_evidence=3, resolved_risks=2, novel_objections=1)
    bad = TriadMetrics(new_evidence=3, repeated_arguments=3, unresolved_high_risk_claims=2)
    assert good.progress_score > bad.progress_score
    assert bad.loop_risk == "HIGH"


def test_dashboard_projects_event_and_claim_state() -> None:
    bus = TriadEventBus()
    bus.publish(
        TriadEvent.create(
            cycle_id="c1",
            actor=TriadRole.BUILDER,
            event_type=TriadEventType.PROPOSAL_CREATED,
            payload={"candidate_id": "x"},
            created_at="2026-08-23T00:00:00+00:00",
        )
    )
    candidate = CandidateArtifact("x", "c1", "builder", "claim", {})
    candidate.attach_measurement(["evd-1"])
    state = TriadDashboardProjector().project(
        cycle_id="c1",
        event_bus=bus,
        candidates=[candidate],
        metrics=TriadMetrics(new_evidence=1),
    )
    assert state.builder_events == 1
    assert state.measured_not_verified == 1
    assert state.verified == 0
    assert state.evidence_gain == 1


def test_provenance_graph_requires_existing_endpoints() -> None:
    graph = ProvenanceGraph()
    source = ProvenanceNode.create(kind="candidate", subject="s", payload={"v": 1})
    target = ProvenanceNode.create(kind="measurement", subject="s", payload={"v": 2})
    graph.add_node(source)
    graph.add_node(target)
    graph.link(source.node_id, target.node_id, "measured_by")
    assert graph.predecessors(target.node_id) == (source,)


def test_measured_candidate_is_not_verified_by_projection() -> None:
    candidate = CandidateArtifact("x", "c1", "builder", "claim", {})
    candidate.attach_measurement(["evd-1"])
    assert candidate.state is ClaimState.MEASURED_NOT_VERIFIED
