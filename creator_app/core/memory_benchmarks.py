from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BenchmarkStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


class MemoryBenchmarkCase(BaseModel):
    case_id: str
    tenant_id: str
    expected_memory_ids: set[str] = Field(default_factory=set)
    forbidden_memory_ids: set[str] = Field(default_factory=set)


class MemoryBenchmarkResult(BaseModel):
    case_id: str
    status: BenchmarkStatus
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    tenant_isolation_ok: bool
    evidence_ids: list[str] = Field(default_factory=list)


class MemoryRegressionBenchmark:
    """Scores retrieval quality and blocks cross-tenant leakage."""

    def evaluate(
        self,
        case: MemoryBenchmarkCase,
        *,
        retrieved_memory_ids: list[str],
        retrieved_tenant_ids: list[str],
        evidence_ids: list[str],
    ) -> MemoryBenchmarkResult:
        if not evidence_ids:
            return MemoryBenchmarkResult(
                case_id=case.case_id,
                status=BenchmarkStatus.BLOCKED,
                precision=0.0,
                recall=0.0,
                tenant_isolation_ok=False,
            )
        retrieved = set(retrieved_memory_ids)
        expected = case.expected_memory_ids
        true_positive = len(retrieved & expected)
        precision = true_positive / len(retrieved) if retrieved else 1.0
        recall = true_positive / len(expected) if expected else 1.0
        tenant_isolation_ok = all(tid == case.tenant_id for tid in retrieved_tenant_ids)
        forbidden_hit = bool(retrieved & case.forbidden_memory_ids)
        status = (
            BenchmarkStatus.PASS
            if tenant_isolation_ok and not forbidden_hit and precision >= 0.8 and recall >= 0.8
            else BenchmarkStatus.FAIL
        )
        return MemoryBenchmarkResult(
            case_id=case.case_id,
            status=status,
            precision=precision,
            recall=recall,
            tenant_isolation_ok=tenant_isolation_ok,
            evidence_ids=evidence_ids,
        )
