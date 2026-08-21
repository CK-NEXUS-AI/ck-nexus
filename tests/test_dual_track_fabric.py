from creator_app.core import (
    Argument,
    AutonomousCapabilityBuilder,
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
    DualTrackCouncil,
    EvidenceGraph,
    RoleType,
    SandboxRequest,
    SandboxRunner,
    StructuredDebateEngine,
)


def test_verified_capability_requires_real_evidence_binding() -> None:
    registry = CapabilityRegistry()
    try:
        registry.register(
            Capability(
                capability_id="sandbox.isolation",
                name="Sandbox Isolation",
                description="Isolation",
                category="security",
                status=CapabilityStatus.VERIFIED,
            )
        )
    except ValueError as exc:
        assert "evidence_ids" in str(exc)
    else:
        raise AssertionError("VERIFIED capability accepted without evidence")


def test_debate_requires_independent_roles_and_honors_veto() -> None:
    engine = StructuredDebateEngine()
    proposal_id = engine.create_proposal(
        title="Add capability",
        description="candidate",
        base_commit="a" * 40,
        base_tree="b" * 40,
    )
    engine.add_argument(
        proposal_id,
        Argument(role=RoleType.ARCHITECT, content="design", score=0.8),
    )
    assert engine.resolve(proposal_id)["decision"] == "PENDING"

    engine.add_argument(
        proposal_id,
        Argument(role=RoleType.VERIFIER, content="tests pass", score=0.7),
    )
    engine.add_argument(
        proposal_id,
        Argument(role=RoleType.RED_TEAM, content="unsafe", veto=True, score=-1.0),
    )
    assert engine.resolve(proposal_id)["decision"] == "REJECT"


def test_evidence_graph_is_append_only_and_parent_bound() -> None:
    graph = EvidenceGraph()
    graph.append(evidence_id="e1", kind="test", subject="s1", payload={"ok": True})
    graph.append(
        evidence_id="e2",
        kind="verify",
        subject="s1",
        payload={"verified": True},
        parents=["e1"],
    )
    assert [node.evidence_id for node in graph.lineage("e2")] == ["e1", "e2"]


def test_sandbox_is_fail_closed_without_attested_executor() -> None:
    runner = SandboxRunner()
    result = runner.run(SandboxRequest(code="print('ok')"))
    assert result.executed is False
    assert result.success is False
    assert "attested sandbox executor" in str(result.reason)


def test_council_allows_only_post_p0_progression() -> None:
    engine = StructuredDebateEngine()
    proposal_id = engine.create_proposal(
        title="Capability",
        description="candidate",
        base_commit="a" * 40,
        base_tree="b" * 40,
    )
    for role, score in [
        (RoleType.ARCHITECT, 0.6),
        (RoleType.VERIFIER, 0.6),
        (RoleType.RED_TEAM, 0.4),
    ]:
        engine.add_argument(
            proposal_id,
            Argument(role=role, content="review", score=score),
        )

    council = DualTrackCouncil(engine)
    decision = council.decide(
        proposal_id=proposal_id,
        track="experimental_lab",
        evidence_ids=["ev-1"],
    )
    assert decision.decision.value == "IMPLEMENT_POST_P0"

    builder = AutonomousCapabilityBuilder()
    assert builder is not None
