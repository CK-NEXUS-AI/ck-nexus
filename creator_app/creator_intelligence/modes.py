"""Transparent prompt-mode registry for CK-NEXUS creator workflows.

These are CK-NEXUS modes, not undocumented or "secret" ChatGPT commands.
User text remains untrusted input and never overrides runtime policy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatorModeSpec:
    id: str
    purpose: str
    output_contract: tuple[str, ...]
    requires_sources: bool = False
    allows_external_publish: bool = False


_MODES: dict[str, CreatorModeSpec] = {
    "expert": CreatorModeSpec(
        id="expert",
        purpose="Produce a domain-aware answer while separating facts, assumptions, and uncertainty.",
        output_contract=("answer", "assumptions", "uncertainty"),
    ),
    "brief": CreatorModeSpec(
        id="brief",
        purpose="Condense material to the smallest useful answer without dropping key constraints.",
        output_contract=("summary", "key_points"),
    ),
    "compare": CreatorModeSpec(
        id="compare",
        purpose="Compare options against explicit criteria and evidence.",
        output_contract=("criteria", "comparison", "tradeoffs", "recommendation"),
    ),
    "research": CreatorModeSpec(
        id="research",
        purpose="Research a topic using attributable sources and distinguish source facts from inference.",
        output_contract=("findings", "sources", "gaps", "next_checks"),
        requires_sources=True,
    ),
    "brainstorm": CreatorModeSpec(
        id="brainstorm",
        purpose="Generate diverse ideas, deduplicate them, and rank by usefulness and feasibility.",
        output_contract=("ideas", "dedup_notes", "ranking"),
    ),
    "seo": CreatorModeSpec(
        id="seo",
        purpose="Improve discoverability using people-first SEO fundamentals without keyword stuffing.",
        output_contract=("search_intent", "structure", "metadata", "quality_checks"),
        requires_sources=True,
    ),
    "ai-search": CreatorModeSpec(
        id="ai-search",
        purpose="Improve answer-engine and generative-search readability through clear structure, evidence, citations, and original value.",
        output_contract=("user_questions", "answer_blocks", "citations", "original_value", "quality_checks"),
        requires_sources=True,
    ),
    "creator": CreatorModeSpec(
        id="creator",
        purpose="Plan original platform-aware creator content with measurable goals.",
        output_contract=("audience", "hook", "body", "cta", "production_notes", "metric"),
    ),
    "repurpose": CreatorModeSpec(
        id="repurpose",
        purpose="Transform source material into platform-native variants while preserving meaning and provenance.",
        output_contract=("source_message", "variants", "provenance_notes"),
    ),
    "privacy-check": CreatorModeSpec(
        id="privacy-check",
        purpose="Review data collection, permissions, personalization, and disclosure risk without overstating privacy claims.",
        output_contract=("data_types", "controls", "risk_notes", "recommended_actions"),
        requires_sources=True,
    ),
}

_ALIASES = {
    "/expert": "expert",
    "/brief": "brief",
    "/compare": "compare",
    "/research": "research",
    "/brainstorm": "brainstorm",
    "/seo": "seo",
    "/geo": "ai-search",
    "/aeo": "ai-search",
    "/creator": "creator",
    "/viral": "creator",
    "/repurpose": "repurpose",
    "/privacy": "privacy-check",
}


def get_mode(name: str) -> CreatorModeSpec:
    normalized = name.strip().lower()
    normalized = _ALIASES.get(normalized, normalized)
    try:
        return _MODES[normalized]
    except KeyError as exc:
        raise KeyError(f"Unknown CK-NEXUS creator mode: {name}") from exc


def list_modes() -> tuple[CreatorModeSpec, ...]:
    return tuple(_MODES[key] for key in sorted(_MODES))
