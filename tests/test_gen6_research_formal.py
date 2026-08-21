from creator_app.core.citation_graph import (
    CitationEdge,
    CitationGraph,
    CitationRelation,
    CitationSource,
    ClaimNode,
    ClaimStatus,
    SourceTrust,
)
from creator_app.core.deep_research import (
    DeepResearchPolicy,
    DeepResearchState,
    ResearchDecision,
    ResearchIteration,
)
from creator_app.core.formal_verification import (
    FormalInvariant,
    FormalLanguage,
    FormalVerificationPolicy,
    ProofReceipt,
    ProofResult,
)
from creator_app.core.hypothesis_tournament import (
    CandidateStatus,
    EvaluationStance,
    HypothesisCandidate,
    HypothesisEvaluation,
    HypothesisTournament,
)
from creator_app.core.research_artifacts import (
    EvaluatorFleetReceipt,
    ReproducibleResearchArtifact,
)


def test_deep_research_requires_iteration_evidence_and_no_external_write() -> None:
    policy = DeepResearchPolicy(minimum_distinct_sources=2)
    ready = DeepResearchState(
        research_id="r1",
        question_digest="sha256:q",
        iterations=(
            ResearchIteration(
                iteration_id="i1",
                objective_digest="sha256:o",
                source_ids=("s1", "s2"),
                evidence_ids=("evd-1",),
            ),
        ),
    )
    assert policy.evaluate(ready) == ResearchDecision.READY_FOR_VERIFICATION

    unsafe = ready.model_copy(
        update={
            "iterations": (
                ready.iterations[0].model_copy(update={"external_write_requested": True}),
            )
        }
    )
    assert policy.evaluate(unsafe) == ResearchDecision.BLOCKED


def test_deep_research_continues_while_gap_is_unresolved() -> None:
    state = DeepResearchState(
        research_id="r1",
        question_digest="sha256:q",
        iterations=(
            ResearchIteration(
                iteration_id="i1",
                objective_digest="sha256:o",
                source_ids=("s1",),
                evidence_ids=("evd-1",),
                unresolved_gap_ids=("gap-1",),
            ),
        ),
    )
    assert DeepResearchPolicy().evaluate(state) == ResearchDecision.CONTINUE


def _citation_graph() -> CitationGraph:
    graph = CitationGraph()
    graph.add_claim(ClaimNode(claim_id="c1", statement_digest="sha256:claim"))
    graph.add_source(
        CitationSource(
            source_id="s1",
            publisher_id="publisher-a",
            artifact_digest="sha256:a",
            trust=SourceTrust.VERIFIED,
            evidence_ids=("evd-source-a",),
        )
    )
    graph.add_source(
        CitationSource(
            source_id="s2",
            publisher_id="publisher-b",
            artifact_digest="sha256:b",
            trust=SourceTrust.TRUSTED,
            evidence_ids=("evd-source-b",),
        )
    )
    return graph


def test_claim_verification_requires_independent_verified_sources() -> None:
    graph = _citation_graph()
    for source_id in ("s1", "s2"):
        graph.add_edge(
            CitationEdge(
                claim_id="c1",
                source_id=source_id,
                relation=CitationRelation.SUPPORTS,
                excerpt_digest=f"sha256:{source_id}",
                verified=True,
                evidence_ids=(f"evd-edge-{source_id}",),
            )
        )
    result = graph.verify_claim("c1")
    assert result.status == ClaimStatus.VERIFIED
    assert result.independent_publishers == 2


def test_verified_contradiction_dominates_claim_status() -> None:
    graph = _citation_graph()
    graph.add_edge(
        CitationEdge(
            claim_id="c1",
            source_id="s1",
            relation=CitationRelation.SUPPORTS,
            excerpt_digest="sha256:support",
            verified=True,
            evidence_ids=("evd-support",),
        )
    )
    graph.add_edge(
        CitationEdge(
            claim_id="c1",
            source_id="s2",
            relation=CitationRelation.CONTRADICTS,
            excerpt_digest="sha256:contradict",
            verified=True,
            evidence_ids=("evd-contradict",),
        )
    )
    assert graph.verify_claim("c1").status == ClaimStatus.CONTRADICTED


def _candidate() -> HypothesisCandidate:
    return HypothesisCandidate(
        candidate_id="h1",
        statement_digest="sha256:h1",
        evidence_ids=("evd-h1",),
    )


def _evaluations(*, veto: bool = False) -> list[HypothesisEvaluation]:
    return [
        HypothesisEvaluation(
            evaluator_id="reviewer-a",
            candidate_id="h1",
            stance=EvaluationStance.SUPPORT,
            correctness=0.9,
            novelty=0.8,
            falsifiability=0.8,
            utility=0.9,
            evidence_ids=("evd-a",),
        ),
        HypothesisEvaluation(
            evaluator_id="reviewer-b",
            candidate_id="h1",
            stance=EvaluationStance.CHALLENGE,
            correctness=0.8,
            novelty=0.7,
            falsifiability=0.9,
            utility=0.8,
            evidence_ids=("evd-b",),
        ),
        HypothesisEvaluation(
            evaluator_id="reviewer-c",
            candidate_id="h1",
            stance=EvaluationStance.SUPPORT,
            correctness=0.9,
            novelty=0.9,
            falsifiability=0.8,
            utility=0.9,
            safety_veto=veto,
            evidence_ids=("evd-c",),
        ),
    ]


def test_hypothesis_tournament_requires_quorum_and_dissent() -> None:
    result = HypothesisTournament().evaluate(_candidate(), _evaluations())
    assert result.status == CandidateStatus.ELIGIBLE
    assert result.evaluator_count == 3
    assert result.challenge_count == 1


def test_hypothesis_tournament_safety_veto_blocks() -> None:
    result = HypothesisTournament().evaluate(_candidate(), _evaluations(veto=True))
    assert result.status == CandidateStatus.BLOCKED


def test_evolution_candidate_never_auto_activates() -> None:
    tournament = HypothesisTournament()
    parent_a = _candidate()
    parent_b = HypothesisCandidate(
        candidate_id="h2",
        statement_digest="sha256:h2",
        generation=2,
        evidence_ids=("evd-h2",),
    )
    child = tournament.propose_offspring(
        candidate_id="h3",
        statement_digest="sha256:h3",
        parents=(parent_a, parent_b),
        evidence_ids=("evd-evolution",),
    )
    assert child.generation == 3
    assert not child.production_activation_allowed


def _proof_receipt(**updates: object) -> ProofReceipt:
    values: dict[str, object] = {
        "invariant_id": "inv-1",
        "subject_digest": "sha256:subject",
        "language": FormalLanguage.LEAN4,
        "checker_id": "lean",
        "checker_version": "4.24.0",
        "theorem_digest": "sha256:theorem",
        "proof_digest": "sha256:proof",
        "result": ProofResult.PASS,
        "evidence_ids": ("evd-proof",),
    }
    values.update(updates)
    return ProofReceipt(**values)


def test_formal_verification_is_exact_subject_and_fail_closed() -> None:
    invariant = FormalInvariant(
        invariant_id="inv-1",
        subject_digest="sha256:subject",
        statement_digest="sha256:statement",
    )
    policy = FormalVerificationPolicy()
    assert policy.verify(invariant, _proof_receipt()).verified
    stale = policy.verify(
        invariant,
        _proof_receipt(subject_digest="sha256:stale"),
    )
    assert not stale.verified
    assert stale.reason == "subject_digest_mismatch"


def test_formal_verification_rejects_unpinned_checker() -> None:
    invariant = FormalInvariant(
        invariant_id="inv-1",
        subject_digest="sha256:subject",
        statement_digest="sha256:statement",
    )
    result = FormalVerificationPolicy().verify(
        invariant,
        _proof_receipt(checker_version="latest"),
    )
    assert not result.verified
    assert result.reason == "checker_version_not_pinned"


def test_reproducible_artifact_requires_pinned_versions_and_evidence() -> None:
    artifact = ReproducibleResearchArtifact(
        artifact_id="artifact-1",
        source_commit="a" * 40,
        source_tree="b" * 40,
        environment_digest="sha256:env",
        input_digests=("sha256:input",),
        output_digests=("sha256:output",),
        evaluator_ids=("eval-a", "eval-b"),
        evidence_ids=("evd-artifact",),
        provider_versions={"research-adapter": "1.2.0"},
    )
    assert artifact.validate_reproducibility()
    floating = artifact.model_copy(
        update={"provider_versions": {"research-adapter": "latest"}}
    )
    assert not floating.validate_reproducibility()


def test_evaluator_fleet_requires_independent_quorum_and_no_veto() -> None:
    receipt = EvaluatorFleetReceipt(
        subject_id="subject-1",
        evaluator_ids=("a", "b", "c"),
        independent_evaluator_ids=("a", "b"),
        evidence_ids=("evd-1",),
    )
    assert receipt.quorum_met()
    assert not receipt.model_copy(update={"safety_veto": True}).quorum_met()
