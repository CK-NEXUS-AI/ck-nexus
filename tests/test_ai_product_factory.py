from __future__ import annotations

import json
from pathlib import Path

from scripts.ai_closure_gate import evaluate
from scripts.ai_idea_harvester import ingest


def test_idea_harvester_preserves_provenance_and_scores() -> None:
    record = ingest({
        "problem": "slow agent deployment",
        "target_user": "developers",
        "solution": "automated governed deployment assistant",
        "market_demand": 90,
        "pain_severity": 90,
        "revenue_potential": 70,
        "competition_gap": 80,
        "technical_feasibility": 90,
        "reusability": 80,
        "automation_fit": 90,
        "strategic_fit": 90,
        "time_to_market": 80,
        "evidence_strength": 70,
        "source": "test",
    })
    assert record["provenance_required"] is True
    assert record["fingerprint"]
    assert record["opportunity_score"] > 0
    assert record["queue"] in {"BUILD_NOW", "PRIORITY", "EXPERIMENT", "BACKLOG"}


def test_closure_gate_rejects_unverified_work() -> None:
    result = evaluate({
        "implementation_evidence": True,
        "test_evidence": True,
        "security_evidence": True,
        "independent_verification": False,
        "provenance": True,
    })
    assert result["status"] == "REPAIR_REQUIRED"
    assert "independent_verification" in result["missing_evidence"]


def test_closure_gate_closes_only_with_all_evidence() -> None:
    result = evaluate({
        "implementation_evidence": True,
        "test_evidence": True,
        "security_evidence": True,
        "independent_verification": True,
        "provenance": True,
        "regression_increased": False,
        "production_mutation": False,
    })
    assert result["status"] == "CLOSED"


def test_factory_config_exists() -> None:
    path = Path(__file__).parents[1] / "config" / "ai_product_factory.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["closure"]["no_evidence_no_done"] is True
