"""Behavioral equivalence verification primitives.

The verifier compares observed outputs and evidence supplied by callers. It
never self-certifies equivalence: VERIFIED is returned only when every declared
case matches and all required contracts are satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    source_output: Any
    target_output: Any
    equivalent: bool
    reason: str | None = None


@dataclass
class EquivalenceReport:
    status: str
    cases: list[CaseResult] = field(default_factory=list)
    contract_checks: dict[str, bool] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"


def verify_equivalence(
    cases: Iterable[tuple[str, Any, Any]],
    *,
    contract_checks: dict[str, bool] | None = None,
    limitations: Iterable[str] = (),
) -> EquivalenceReport:
    """Compare source/target observations using strict equality by default.

    Higher-level differential/property/golden runners can feed their results
    into this function. Any mismatch or failed contract prevents verification.
    """
    results = [
        CaseResult(case_id=case_id, source_output=source, target_output=target, equivalent=source == target,
                   reason=None if source == target else "observable output mismatch")
        for case_id, source, target in cases
    ]
    checks = dict(contract_checks or {})
    all_cases = bool(results) and all(item.equivalent for item in results)
    all_contracts = all(checks.values()) if checks else True
    status = "VERIFIED" if all_cases and all_contracts else "NOT_VERIFIED"
    return EquivalenceReport(
        status=status,
        cases=results,
        contract_checks=checks,
        limitations=list(limitations),
    )
