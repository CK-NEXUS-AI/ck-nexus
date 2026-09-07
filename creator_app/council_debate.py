"""Deterministic moderation for CK-NEXUS Development Council debate mode."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class DebateRole(StrEnum):
    PROPOSER = "PROPOSER"
    OPPOSER = "OPPOSER"
    EXAMINER = "EXAMINER"
    SYNTHESIZER = "SYNTHESIZER"


class DebateStance(StrEnum):
    SUPPORT = "SUPPORT"
    OPPOSE = "OPPOSE"
    UNCERTAIN = "UNCERTAIN"
    SYNTHESIS = "SYNTHESIS"


class DebateStatus(StrEnum):
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    MORE_EVIDENCE_REQUIRED = "MORE_EVIDENCE_REQUIRED"
    DISAGREEMENT_REMAINS = "DISAGREEMENT_REMAINS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class DebatePolicy:
    max_rounds: int = 10
    max_words_per_turn: int = 300
    consensus_threshold: float = 0.8
    no_new_round_limit: int = 2

    def __post_init__(self) -> None:
        if not 1 <= self.max_rounds <= 10:
            raise ValueError("max_rounds must be between 1 and 10")
        if not 50 <= self.max_words_per_turn <= 1000:
            raise ValueError("max_words_per_turn must be between 50 and 1000")
        if not 0.5 <= self.consensus_threshold <= 1.0:
            raise ValueError("consensus_threshold must be between 0.5 and 1.0")
        if not 1 <= self.no_new_round_limit <= self.max_rounds:
            raise ValueError("no_new_round_limit must be within max_rounds")


@dataclass(frozen=True, slots=True)
class DebateContribution:
    role: DebateRole
    stance: DebateStance
    confidence: float
    summary: str
    evidence_refs: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    safety_concern: bool = False

    @property
    def fingerprint(self) -> str:
        normalized = re.sub(r"\s+", " ", self.summary.casefold()).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DebateModeration:
    status: DebateStatus
    consensus_score: float
    evidence_refs: tuple[str, ...]
    reasons: tuple[str, ...]
    rule_violations: tuple[str, ...]
    authority_effect: str = "NONE"


def parse_contribution(
    raw: str,
    *,
    role: DebateRole,
    policy: DebatePolicy | None = None,
) -> tuple[DebateContribution, tuple[str, ...]]:
    resolved_policy = policy or DebatePolicy()
    data = _extract_json_object(raw)
    stance = _parse_stance(data.get("stance"), role=role)
    confidence = _parse_confidence(data.get("confidence"))
    summary = str(data.get("summary") or "").strip()
    if not summary:
        raise ValueError("debate contribution summary is required")

    violations: list[str] = []
    word_count = len(summary.split())
    if word_count > resolved_policy.max_words_per_turn:
        violations.append(
            f"{role.value}:word_limit_exceeded:{word_count}>{resolved_policy.max_words_per_turn}"
        )

    contribution = DebateContribution(
        role=role,
        stance=stance,
        confidence=confidence,
        summary=summary,
        evidence_refs=_clean_string_tuple(data.get("evidence_refs"), limit=32),
        claims=_clean_string_tuple(data.get("claims"), limit=16),
        risks=_clean_string_tuple(data.get("risks"), limit=16),
        questions=_clean_string_tuple(data.get("questions"), limit=16),
        safety_concern=bool(data.get("safety_concern", False)),
    )
    return contribution, tuple(violations)


def moderate_votes(
    votes: Iterable[DebateContribution],
    *,
    policy: DebatePolicy | None = None,
    extra_violations: Iterable[str] = (),
) -> DebateModeration:
    resolved_policy = policy or DebatePolicy()
    vote_list = list(votes)
    allowed_roles = {DebateRole.PROPOSER, DebateRole.OPPOSER, DebateRole.EXAMINER}
    if {vote.role for vote in vote_list} != allowed_roles or len(vote_list) != 3:
        raise ValueError("final moderation requires exactly proposer, opposer, and examiner votes")

    violations = list(extra_violations)
    fingerprints: set[str] = set()
    for vote in vote_list:
        if vote.fingerprint in fingerprints:
            violations.append(f"{vote.role.value}:duplicate_turn")
        fingerprints.add(vote.fingerprint)

    evidence_refs = tuple(
        dict.fromkeys(ref for vote in vote_list for ref in vote.evidence_refs)
    )
    stance_value = {
        DebateStance.SUPPORT: 1.0,
        DebateStance.UNCERTAIN: 0.5,
        DebateStance.OPPOSE: 0.0,
    }
    score = sum(stance_value[vote.stance] for vote in vote_list) / len(vote_list)
    score = round(score, 3)

    reasons: list[str] = []
    if any(vote.safety_concern for vote in vote_list):
        status = DebateStatus.HUMAN_REVIEW_REQUIRED
        reasons.append("one or more reviewers raised a safety concern")
    elif violations:
        status = DebateStatus.HUMAN_REVIEW_REQUIRED
        reasons.append("deterministic debate rules were violated")
    elif score >= resolved_policy.consensus_threshold:
        status = DebateStatus.CONSENSUS_REACHED
        reasons.append("advisory vote threshold reached")
    elif any(vote.stance is DebateStance.UNCERTAIN for vote in vote_list):
        status = DebateStatus.MORE_EVIDENCE_REQUIRED
        reasons.append("at least one reviewer remains uncertain")
    else:
        status = DebateStatus.DISAGREEMENT_REMAINS
        reasons.append("advisory vote threshold not reached")

    if not evidence_refs:
        reasons.append("no external evidence references were supplied")
        if status is DebateStatus.CONSENSUS_REACHED:
            reasons.append("consensus is advisory only and cannot establish verification")

    return DebateModeration(
        status=status,
        consensus_score=score,
        evidence_refs=evidence_refs,
        reasons=tuple(reasons),
        rule_violations=tuple(dict.fromkeys(violations)),
    )


def build_initial_prompt(
    role: DebateRole,
    *,
    objective: str,
    context: str,
    language: str,
    prior: Iterable[DebateContribution] = (),
) -> str:
    if role is DebateRole.SYNTHESIZER:
        raise ValueError("use build_synthesis_prompt for synthesizer")

    role_instruction = {
        DebateRole.PROPOSER: (
            "Propose the strongest practical resolution. State assumptions, evidence, trade-offs, "
            "and failure modes."
        ),
        DebateRole.OPPOSER: (
            "Challenge the proposal. Identify hidden assumptions, counterexamples, unsafe paths, "
            "and stronger alternatives."
        ),
        DebateRole.EXAMINER: (
            "Audit factual support and reasoning quality. Separate evidence from inference and "
            "identify what must be verified."
        ),
    }[role]
    payload = {
        "objective": objective,
        "context": context,
        "language": language,
        "prior_contributions": [_compact_contribution(item) for item in prior],
    }
    return (
        f"You are the {role.value} in CK-NEXUS Debate Protocol V1. {role_instruction}\n"
        "The debate is advisory only. Do not perform side effects or claim verification.\n"
        "Reply with one JSON object only using this schema:\n"
        '{"stance":"SUPPORT|OPPOSE|UNCERTAIN","confidence":0.0,'
        '"summary":"<=300 words","evidence_refs":[],"claims":[],"risks":[],'
        '"questions":[],"safety_concern":false}\n'
        f"INPUT\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    )


def build_synthesis_prompt(
    *,
    objective: str,
    context: str,
    language: str,
    contributions: Iterable[DebateContribution],
) -> str:
    payload = {
        "objective": objective,
        "context": context,
        "language": language,
        "contributions": [_compact_contribution(item) for item in contributions],
    }
    return (
        "You are the SYNTHESIZER in CK-NEXUS Debate Protocol V1. Reconcile the strongest supported "
        "points, preserve unresolved disagreement, and draft one reviewable resolution. "
        "Do not claim verification or authority.\n"
        "Reply with one JSON object only using this schema:\n"
        '{"stance":"SYNTHESIS","confidence":0.0,"summary":"<=300 words",'
        '"evidence_refs":[],"claims":[],"risks":[],"questions":[],"safety_concern":false}\n'
        f"INPUT\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    )


def build_final_vote_prompt(
    role: DebateRole,
    *,
    objective: str,
    synthesis: DebateContribution,
    language: str,
) -> str:
    if role not in {DebateRole.PROPOSER, DebateRole.OPPOSER, DebateRole.EXAMINER}:
        raise ValueError("final vote role must be proposer, opposer, or examiner")
    payload = {
        "objective": objective,
        "language": language,
        "draft_resolution": _compact_contribution(synthesis),
    }
    return (
        f"You are the {role.value} conducting the final independent review of the drafted "
        "resolution. Vote SUPPORT only if the resolution is acceptable as an advisory "
        "recommendation. Vote OPPOSE for a material defect. Vote UNCERTAIN when more evidence is "
        "needed. A safety concern must be explicit. Do not claim verification.\n"
        "Reply with one JSON object only using this schema:\n"
        '{"stance":"SUPPORT|OPPOSE|UNCERTAIN","confidence":0.0,'
        '"summary":"<=300 words","evidence_refs":[],"claims":[],"risks":[],'
        '"questions":[],"safety_concern":false}\n'
        f"INPUT\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    )


def render_report(
    *,
    objective: str,
    initial: Iterable[DebateContribution],
    synthesis: DebateContribution,
    final_votes: Iterable[DebateContribution],
    moderation: DebateModeration,
) -> str:
    lines = [
        "# CK-NEXUS Debate Protocol V1",
        "",
        f"Objective: {objective}",
        "",
        "## Initial positions",
    ]
    for item in initial:
        lines.extend(_render_contribution(item))
    lines.extend(["", "## Synthesized resolution"])
    lines.extend(_render_contribution(synthesis))
    lines.extend(["", "## Final independent votes"])
    for item in final_votes:
        lines.extend(_render_contribution(item))
    lines.extend(
        [
            "",
            "## Deterministic moderation",
            f"- status: {moderation.status.value}",
            f"- consensus_score: {moderation.consensus_score:.3f}",
            f"- evidence_refs: {len(moderation.evidence_refs)}",
            f"- authority_effect: {moderation.authority_effect}",
        ]
    )
    for reason in moderation.reasons:
        lines.append(f"- reason: {reason}")
    for violation in moderation.rule_violations:
        lines.append(f"- rule_violation: {violation}")
    lines.extend(
        [
            "",
            "This result is advisory. It is not independent human review, VERIFIED status, "
            "Production authorization, or owner sign-off.",
        ]
    )
    return "\n".join(lines)


def build_mock_debate_report(objective: str) -> str:
    initial = (
        DebateContribution(
            DebateRole.PROPOSER,
            DebateStance.SUPPORT,
            0.75,
            "Use the existing Development Council and add a bounded debate protocol instead of "
            "building a second agent runtime.",
            ("repo:creator_app/dev_team.py",),
        ),
        DebateContribution(
            DebateRole.OPPOSER,
            DebateStance.OPPOSE,
            0.7,
            "The design must prevent a model-based moderator from granting authority and must "
            "preserve fail-closed execution gates.",
            ("repo:creator_app/council_authority/arbitration.py",),
        ),
        DebateContribution(
            DebateRole.EXAMINER,
            DebateStance.UNCERTAIN,
            0.65,
            "The existing Council and Provider Router should be reused, but cross-provider role "
            "routing requires separate compatibility and privacy verification.",
            ("repo:creator_app/provider_router.py",),
        ),
    )
    synthesis = DebateContribution(
        DebateRole.SYNTHESIZER,
        DebateStance.SYNTHESIS,
        0.8,
        "Adopt Debate Protocol V1 as an advisory Council mode with deterministic moderation, "
        "evidence references, bounded turns, and human escalation. Defer cross-provider role "
        "routing until provider registry reconciliation is measured.",
        tuple(dict.fromkeys(ref for item in initial for ref in item.evidence_refs)),
    )
    final_votes = (
        DebateContribution(
            DebateRole.PROPOSER,
            DebateStance.SUPPORT,
            0.85,
            "The synthesized resolution preserves reuse and staged delivery.",
            synthesis.evidence_refs,
        ),
        DebateContribution(
            DebateRole.OPPOSER,
            DebateStance.SUPPORT,
            0.8,
            "The resolution addresses the authority concern by keeping moderation deterministic.",
            synthesis.evidence_refs,
        ),
        DebateContribution(
            DebateRole.EXAMINER,
            DebateStance.SUPPORT,
            0.8,
            "The resolution clearly separates implemented protocol work from unverified provider "
            "expansion.",
            synthesis.evidence_refs,
        ),
    )
    moderation = moderate_votes(final_votes)
    return render_report(
        objective=objective,
        initial=initial,
        synthesis=synthesis,
        final_votes=final_votes,
        moderation=moderation,
    )


def _extract_json_object(raw: str) -> dict[str, object]:
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("debate contribution must contain one JSON object")
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("debate contribution contains invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("debate contribution must be a JSON object")
    return value


def _parse_stance(value: object, *, role: DebateRole) -> DebateStance:
    raw = str(value or "").strip().upper()
    try:
        stance = DebateStance(raw)
    except ValueError as exc:
        raise ValueError("invalid debate stance") from exc
    if role is DebateRole.SYNTHESIZER and stance is not DebateStance.SYNTHESIS:
        raise ValueError("synthesizer must return SYNTHESIS stance")
    if role is not DebateRole.SYNTHESIZER and stance is DebateStance.SYNTHESIS:
        raise ValueError("non-synthesizer cannot return SYNTHESIS stance")
    return stance


def _parse_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("debate confidence must be numeric") from exc
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("debate confidence must be between 0 and 1")
    return confidence


def _clean_string_tuple(value: object, *, limit: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("debate list fields must be JSON arrays")
    cleaned = []
    for item in value[:limit]:
        text = str(item).strip()
        if text:
            cleaned.append(text[:1000])
    return tuple(dict.fromkeys(cleaned))


def _compact_contribution(item: DebateContribution) -> dict[str, object]:
    return {
        "role": item.role.value,
        "stance": item.stance.value,
        "confidence": item.confidence,
        "summary": item.summary,
        "evidence_refs": list(item.evidence_refs),
        "claims": list(item.claims),
        "risks": list(item.risks),
        "questions": list(item.questions),
        "safety_concern": item.safety_concern,
    }


def _render_contribution(item: DebateContribution) -> list[str]:
    return [
        f"- {item.role.value}: {item.stance.value} confidence={item.confidence:.2f}",
        f"  {item.summary}",
        f"  evidence_refs={list(item.evidence_refs)}",
    ]
