from idea_engine.retrieval_evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluationSummary,
    RetrievalQualityGate,
    assess_candidate,
    evaluate_case,
    summarize_results,
)


def test_evaluate_case_computes_precision_recall_mrr_and_hit() -> None:
    result = evaluate_case(
        RetrievalEvaluationCase(
            case_id="rag-1",
            query="agent evidence",
            relevant_claim_ids=("c2", "c3"),
            retrieved_claim_ids=("c1", "c2", "c4", "c3"),
            k=3,
        )
    )

    assert result.precision_at_k == 1 / 3
    assert result.recall_at_k == 1 / 2
    assert result.reciprocal_rank == 1 / 2
    assert result.hit_at_k == 1.0


def test_duplicate_retrieved_ids_do_not_inflate_metrics() -> None:
    result = evaluate_case(
        RetrievalEvaluationCase(
            case_id="dedupe",
            query="fresh source",
            relevant_claim_ids=("c1",),
            retrieved_claim_ids=("c1", "c1", "c2"),
            k=2,
        )
    )

    assert result.relevant_found == 1
    assert result.retrieved_considered == 2
    assert result.precision_at_k == 0.5
    assert result.recall_at_k == 1.0


def test_summary_is_macro_average() -> None:
    first = evaluate_case(
        RetrievalEvaluationCase(
            case_id="a",
            query="alpha",
            relevant_claim_ids=("c1",),
            retrieved_claim_ids=("c1",),
            k=1,
        )
    )
    second = evaluate_case(
        RetrievalEvaluationCase(
            case_id="b",
            query="beta",
            relevant_claim_ids=("c2",),
            retrieved_claim_ids=("c3",),
            k=1,
        )
    )

    summary = summarize_results((first, second))
    assert summary.case_count == 2
    assert summary.macro_precision_at_k == 0.5
    assert summary.macro_recall_at_k == 0.5
    assert summary.mean_reciprocal_rank == 0.5
    assert summary.hit_rate_at_k == 0.5


def test_quality_gate_rejects_regression() -> None:
    baseline = RetrievalEvaluationSummary(
        case_count=5,
        macro_precision_at_k=0.7,
        macro_recall_at_k=0.8,
        mean_reciprocal_rank=0.75,
        hit_rate_at_k=0.9,
    )
    candidate = RetrievalEvaluationSummary(
        case_count=5,
        macro_precision_at_k=0.72,
        macro_recall_at_k=0.60,
        mean_reciprocal_rank=0.50,
        hit_rate_at_k=0.8,
    )

    decision = assess_candidate(
        baseline=baseline,
        candidate=candidate,
        gate=RetrievalQualityGate(
            minimum_macro_recall_at_k=0.65,
            minimum_mean_reciprocal_rank=0.55,
            maximum_recall_regression=0.05,
            maximum_mrr_regression=0.05,
        ),
    )

    assert decision.passed is False
    assert "candidate recall is below minimum" in decision.reasons
    assert "candidate MRR is below minimum" in decision.reasons
    assert "candidate recall regression exceeds allowance" in decision.reasons
    assert "candidate MRR regression exceeds allowance" in decision.reasons


def test_quality_gate_accepts_non_regressing_candidate() -> None:
    baseline = RetrievalEvaluationSummary(
        case_count=4,
        macro_precision_at_k=0.6,
        macro_recall_at_k=0.7,
        mean_reciprocal_rank=0.65,
        hit_rate_at_k=0.75,
    )
    candidate = RetrievalEvaluationSummary(
        case_count=4,
        macro_precision_at_k=0.7,
        macro_recall_at_k=0.75,
        mean_reciprocal_rank=0.70,
        hit_rate_at_k=0.8,
    )

    decision = assess_candidate(
        baseline=baseline,
        candidate=candidate,
        gate=RetrievalQualityGate(
            minimum_macro_recall_at_k=0.70,
            minimum_mean_reciprocal_rank=0.65,
        ),
    )

    assert decision.passed is True
    assert decision.reasons == ()


def test_case_bounds_fail_closed() -> None:
    cases = (
        {
            "case_id": "",
            "query": "x",
            "relevant_claim_ids": ("c1",),
            "retrieved_claim_ids": (),
        },
        {
            "case_id": "x",
            "query": "",
            "relevant_claim_ids": ("c1",),
            "retrieved_claim_ids": (),
        },
        {
            "case_id": "x",
            "query": "q",
            "relevant_claim_ids": (),
            "retrieved_claim_ids": (),
        },
        {
            "case_id": "x",
            "query": "q",
            "relevant_claim_ids": ("c1",),
            "retrieved_claim_ids": (),
            "k": 0,
        },
    )
    for kwargs in cases:
        try:
            RetrievalEvaluationCase(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid evaluation case must fail closed")
