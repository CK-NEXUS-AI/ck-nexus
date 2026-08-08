from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from idea_engine.engine import IdeaEngine
from idea_engine.graph import IdeaGraph, text_similarity
from idea_engine.lenses import select_lenses
from idea_engine.models import IdeaFeatures, OpportunityInputs
from idea_engine.scoring import opportunity_score


def engine():
    path = Path(tempfile.mkdtemp()) / "ideas.json"
    return IdeaEngine(IdeaGraph(path))


def score_inputs(**overrides):
    base = dict(
        user_value=0.9,
        strategic_fit=0.8,
        reuse_potential=0.8,
        automation_gain=0.9,
        revenue_potential=0.7,
        evidence_strength=0.6,
        reversibility=0.8,
        risk=0.3,
        implementation_cost=0.4,
    )
    base.update(overrides)
    return OpportunityInputs(**base)


def test_lens_selector_returns_at_most_three_lenses():
    lenses = select_lenses(IdeaFeatures("architecture", uncertainty=0.8, novelty=0.8, risk=0.7))
    assert 1 <= len(lenses) <= 3
    assert "system_design" in lenses or "security_governance" in lenses


def test_opportunity_scoring_is_deterministic_and_risk_reduces_score():
    low_risk = opportunity_score(score_inputs(risk=0.1))
    high_risk = opportunity_score(score_inputs(risk=0.9))
    assert low_risk == opportunity_score(score_inputs(risk=0.1))
    assert low_risk > high_risk


def test_graph_preserves_similar_nodes_and_creates_typed_edge():
    e = engine()
    features = IdeaFeatures("architecture", novelty=0.8)
    first, _, _ = e.expand(
        title="Distributed API Gateway rate limiting",
        raw_input="Use Redis shared rate limit across gateway instances",
        features=features,
        tags=["gateway", "redis"],
    )
    second, links, _ = e.expand(
        title="Distributed API Gateway rate limiter",
        raw_input="Use Redis shared rate limit across multiple gateway instances",
        features=features,
        tags=["gateway", "redis"],
    )
    assert first.id != second.id
    assert links
    assert links[0].type in {"extends", "alternative_to"}
    assert len(e.graph.nodes) == 2


def test_proposal_packet_targets_r10_product_idea_pattern():
    e = engine()
    node, _, _ = e.expand(
        title="Idea Engine pack",
        raw_input="Productize reusable idea workflows",
        features=IdeaFeatures("product"),
    )
    packet = e.make_proposal(node=node, score_inputs=score_inputs(), benefits=["reuse"])
    assert packet.recommended_pattern == "product_idea_exploration"
    assert packet.requires_human_approval is True
    assert 0 <= packet.opportunity_score <= 1


def test_idea_engine_rejects_side_effect_capabilities():
    e = engine()
    for capability in ("deploy", "external_send", "billing_mutation", "credential_export"):
        with pytest.raises(PermissionError):
            e.assert_capability_allowed(capability)


def test_safe_export_has_no_secret_fields():
    e = engine()
    e.expand(title="Safe graph", raw_input="metadata only", features=IdeaFeatures("product"))
    raw = str(e.graph.export_safe()).lower()
    assert "api_key" not in raw
    assert "password" not in raw
    assert "credential_value" not in raw


def test_similarity_is_stable():
    assert text_similarity("redis gateway rate limit", "redis gateway limiter") > 0.4


def test_graph_update_preserves_audit_history_and_archives_instead_of_overwrite():
    e = engine()
    node, _, _ = e.expand(title="History", raw_input="original", features=IdeaFeatures("product"))
    e.graph.update_node(node.id, summary="revised", actor="reviewer")
    e.graph.archive_node(node.id, actor="owner")
    actions = [item["action"] for item in e.graph.history]
    assert actions.count("node_updated") == 2
    assert e.graph.get_node(node.id).status == "archived"
    assert e.graph.history[-2]["before"]["summary"] == "original"
