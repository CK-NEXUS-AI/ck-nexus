from __future__ import annotations

from .models import IdeaFeatures

LENS_REGISTRY = (
    "swot",
    "business_model_canvas",
    "blue_ocean",
    "design_thinking",
    "jobs_to_be_done",
    "cost_risk_impact",
    "system_design",
    "security_governance",
    "automation_opportunity",
    "productization",
)


def select_lenses(features: IdeaFeatures) -> tuple[str, ...]:
    scores: dict[str, float] = {lens: 0.0 for lens in LENS_REGISTRY}
    kind = features.idea_type.lower()
    if kind in {"architecture", "process"}:
        scores["system_design"] += 1.0
        scores["automation_opportunity"] += 0.8
    if kind in {"security", "architecture"} or features.risk >= 0.6:
        scores["security_governance"] += 1.2
        scores["cost_risk_impact"] += 0.6
    if kind in {"product", "business", "marketing"}:
        scores["jobs_to_be_done"] += 0.9
        scores["business_model_canvas"] += 0.8
        scores["productization"] += 0.8
    if features.novelty >= 0.7:
        scores["blue_ocean"] += 1.0
        scores["design_thinking"] += 0.7
    if features.uncertainty >= 0.7:
        scores["swot"] += 0.7
        scores["design_thinking"] += 0.6
    if features.evidence_availability < 0.4:
        scores["cost_risk_impact"] += 0.5
    ranked = sorted(scores, key=lambda lens: (-scores[lens], lens))
    count = 3 if max(scores.values(), default=0) > 0 else 1
    return tuple(ranked[:count])
