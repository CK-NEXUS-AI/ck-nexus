"""Deterministic retrieval quality evaluation for CK-NEXUS knowledge search."""

from __future__ import annotations

from dataclasses import dataclass


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    case_id: str
    query: str
    relevant_claim_ids: tuple[str, ...]
    retrieved_claim_ids: tuple[str, ...]
    k: int = 10
    as_of: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if not self.query.strip():
            raise ValueError("query is required")
        if not self.relevant_claim_ids:
            raise ValueError("relevant_claim_ids must not be empty")
        if not 1 <= self.k <= 100:
            raise ValueError("k must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    case_id: str
    k: int
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    hit_at_k: float
    relevant_found: int
    relevant_total: int
    retrieved_considered: int


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSummary:
    case_count: int
    macro_precision_at_k: float
    macro_recall_at_k: float
    mean_reciprocal_rank: float
    hit_rate_at_k: float


@dataclass(frozen=True, slots=True)
class RetrievalQualityGate:
    minimum_macro_recall_at_k: float = 0.0
    minimum_mean_reciprocal_rank: float = 0.0
    maximum_recall_regression: float = 0.0
    maximum_mrr_regression: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum_macro_recall_at_k", self.minimum_macro_recall_at_k),
            ("minimum_mean_reciprocal_rank", self.minimum_mean_reciprocal_rank),
            ("maximum_recall_regression", self.maximum_recall_regression),
            ("maximum_mrr_regression", self.maximum_mrr_regression),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class RetrievalQualityDecision:
    passed: bool
    reasons: tuple[str, ...]
    recall_delta: float
    mrr_delta: float


def evaluate_case(case: RetrievalEvaluationCase) -> RetrievalEvaluationResult:
    relevant = set(_dedupe(case.relevant_claim_ids))
    retrieved = _dedupe(case.retrieved_claim_ids)
    top_k = retrieved[: case.k]

    relevant_found = sum(1 for claim_id in top_k if claim_id in relevant)
    precision = relevant_found / len(top_k) if top_k else 0.0
    recall = relevant_found / len(relevant)

    reciprocal_rank = 0.0
    for index, claim_id in enumerate(retrieved, start=1):
        if claim_id in relevant:
            reciprocal_rank = 1.0 / index
            break

    return RetrievalEvaluationResult(
        case_id=case.case_id,
        k=case.k,
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        hit_at_k=1.0 if relevant_found else 0.0,
        relevant_found=relevant_found,
        relevant_total=len(relevant),
        retrieved_considered=len(top_k),
    )


def summarize_results(
    results: tuple[RetrievalEvaluationResult, ...],
) -> RetrievalEvaluationSummary:
    if not results:
        raise ValueError("results must not be empty")

    count = len(results)
    return RetrievalEvaluationSummary(
        case_count=count,
        macro_precision_at_k=sum(item.precision_at_k for item in results) / count,
        macro_recall_at_k=sum(item.recall_at_k for item in results) / count,
        mean_reciprocal_rank=sum(item.reciprocal_rank for item in results) / count,
        hit_rate_at_k=sum(item.hit_at_k for item in results) / count,
    )


def assess_candidate(
    *,
    baseline: RetrievalEvaluationSummary,
    candidate: RetrievalEvaluationSummary,
    gate: RetrievalQualityGate,
) -> RetrievalQualityDecision:
    recall_delta = candidate.macro_recall_at_k - baseline.macro_recall_at_k
    mrr_delta = candidate.mean_reciprocal_rank - baseline.mean_reciprocal_rank

    reasons: list[str] = []
    if candidate.macro_recall_at_k < gate.minimum_macro_recall_at_k:
        reasons.append("candidate recall is below minimum")
    if candidate.mean_reciprocal_rank < gate.minimum_mean_reciprocal_rank:
        reasons.append("candidate MRR is below minimum")
    if recall_delta < -gate.maximum_recall_regression:
        reasons.append("candidate recall regression exceeds allowance")
    if mrr_delta < -gate.maximum_mrr_regression:
        reasons.append("candidate MRR regression exceeds allowance")

    return RetrievalQualityDecision(
        passed=not reasons,
        reasons=tuple(reasons),
        recall_delta=recall_delta,
        mrr_delta=mrr_delta,
    )
