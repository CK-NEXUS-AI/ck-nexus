from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BenchmarkStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class MemoryBenchmarkCase(BaseModel):
    case_id: str = Field(min_length=1)
    expected_ids: set[str] = Field(default_factory=set)
    recalled_ids: set[str] = Field(default_factory=set)


class MemoryRegressionPolicy(BaseModel):
    minimum_recall: float = Field(default=0.8, ge=0, le=1)
    minimum_precision: float = Field(default=0.8, ge=0, le=1)
    minimum_cases: int = Field(default=1, ge=1)


class MemoryBenchmarkResult(BaseModel):
    status: BenchmarkStatus
    case_count: int = Field(ge=0)
    recall: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    failed_case_ids: list[str] = Field(default_factory=list)


class MemoryRegressionBenchmark:
    """Evaluates deterministic recall regressions and fails closed on weak evidence."""

    def __init__(self, policy: MemoryRegressionPolicy | None = None) -> None:
        self.policy = policy or MemoryRegressionPolicy()

    def evaluate(self, cases: list[MemoryBenchmarkCase]) -> MemoryBenchmarkResult:
        if len(cases) < self.policy.minimum_cases:
            return MemoryBenchmarkResult(
                status=BenchmarkStatus.FAIL,
                case_count=len(cases),
                recall=0.0,
                precision=0.0,
                failed_case_ids=[case.case_id for case in cases],
            )

        expected_total = sum(len(case.expected_ids) for case in cases)
        recalled_total = sum(len(case.recalled_ids) for case in cases)
        correct_total = sum(
            len(case.expected_ids & case.recalled_ids) for case in cases
        )
        recall = correct_total / expected_total if expected_total else 1.0
        precision = correct_total / recalled_total if recalled_total else 1.0

        failed_case_ids = [
            case.case_id
            for case in cases
            if not case.expected_ids.issubset(case.recalled_ids)
        ]
        passed = (
            recall >= self.policy.minimum_recall
            and precision >= self.policy.minimum_precision
            and not failed_case_ids
        )
        return MemoryBenchmarkResult(
            status=BenchmarkStatus.PASS if passed else BenchmarkStatus.FAIL,
            case_count=len(cases),
            recall=recall,
            precision=precision,
            failed_case_ids=failed_case_ids,
        )
