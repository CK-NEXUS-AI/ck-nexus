from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TriadMetrics:
    new_evidence: int = 0
    resolved_risks: int = 0
    novel_objections: int = 0
    uncertainty_reduction: float = 0.0
    repeated_arguments: int = 0
    duplicate_searches: int = 0
    unresolved_high_risk_claims: int = 0

    @property
    def evidence_gain(self) -> int:
        return self.new_evidence + self.resolved_risks + self.novel_objections

    @property
    def progress_score(self) -> float:
        positive = (
            float(self.new_evidence)
            + float(self.resolved_risks)
            + float(self.novel_objections)
            + max(0.0, self.uncertainty_reduction)
        )
        negative = (
            float(self.repeated_arguments)
            + float(self.duplicate_searches)
            + 2.0 * float(self.unresolved_high_risk_claims)
        )
        return positive - negative

    @property
    def loop_risk(self) -> str:
        if self.repeated_arguments >= 3 or self.duplicate_searches >= 3:
            return "HIGH"
        if self.repeated_arguments >= 1 or self.duplicate_searches >= 1:
            return "MEDIUM"
        return "LOW"
