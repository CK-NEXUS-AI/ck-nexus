from __future__ import annotations

from .models import OpportunityInputs


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def opportunity_score(values: OpportunityInputs) -> float:
    score = (
        0.25 * _unit(values.user_value)
        + 0.20 * _unit(values.strategic_fit)
        + 0.15 * _unit(values.reuse_potential)
        + 0.15 * _unit(values.automation_gain)
        + 0.10 * _unit(values.revenue_potential)
        + 0.10 * _unit(values.evidence_strength)
        + 0.05 * _unit(values.reversibility)
        - 0.20 * _unit(values.risk)
        - 0.15 * _unit(values.implementation_cost)
    )
    return round(max(0.0, min(1.0, score)), 4)
