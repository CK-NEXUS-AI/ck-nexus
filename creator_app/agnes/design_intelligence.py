from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class DesignVerdict(StrEnum):
    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DesignConstraint:
    name: str
    satisfied: bool
    reason: str = ""
    blocking: bool = True


@dataclass(frozen=True, slots=True)
class DesignEvidence:
    evidence_id: str
    kind: str
    subject: str
    summary: str


@dataclass(frozen=True, slots=True)
class DesignProposal:
    proposal_id: str
    goal: str
    users: tuple[str, ...]
    functions: tuple[str, ...]
    constraints: tuple[DesignConstraint, ...] = ()
    evidence: tuple[DesignEvidence, ...] = ()
    alternatives_considered: tuple[str, ...] = ()
    security_reviewed: bool = False
    accessibility_reviewed: bool = False
    implementation_feasible: bool = False


@dataclass(frozen=True, slots=True)
class DesignAssessment:
    proposal_id: str
    verdict: DesignVerdict
    score: int
    reasons: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    invariant_failures: tuple[str, ...]
    principles: dict[str, bool] = field(default_factory=dict)


_REQUIRED_EVIDENCE_KINDS = frozenset({"requirements", "security", "verification"})


def _non_empty(values: Iterable[str]) -> bool:
    return any(value.strip() for value in values)


def assess_design(proposal: DesignProposal) -> DesignAssessment:
    """Evaluate a proposal against deterministic governed-design invariants."""

    reasons: list[str] = []
    invariant_failures: list[str] = []

    blocking_failures = [
        constraint
        for constraint in proposal.constraints
        if constraint.blocking and not constraint.satisfied
    ]
    for constraint in blocking_failures:
        detail = f": {constraint.reason}" if constraint.reason else ""
        invariant_failures.append(f"{constraint.name}{detail}")

    evidence_kinds = {item.kind.strip().lower() for item in proposal.evidence}
    missing_evidence = sorted(_REQUIRED_EVIDENCE_KINDS - evidence_kinds)

    principles = {
        "function_first": bool(proposal.goal.strip()) and _non_empty(proposal.functions),
        "user_centered": _non_empty(proposal.users),
        "governed_design": not invariant_failures and proposal.security_reviewed,
        "iterative_verifiable": bool(proposal.alternatives_considered)
        and not missing_evidence,
        "accessible": proposal.accessibility_reviewed,
        "feasible": proposal.implementation_feasible,
    }

    weights = {
        "function_first": 20,
        "user_centered": 15,
        "governed_design": 25,
        "iterative_verifiable": 20,
        "accessible": 10,
        "feasible": 10,
    }
    score = sum(weights[name] for name, passed in principles.items() if passed)

    if invariant_failures:
        verdict = DesignVerdict.BLOCKED
        reasons.append("One or more blocking design invariants are unsatisfied.")
    elif not principles["governed_design"]:
        verdict = DesignVerdict.BLOCKED
        reasons.append("Security/governance review is required before design approval.")
    elif missing_evidence:
        verdict = DesignVerdict.NEEDS_REVISION
        reasons.append("Required design evidence is incomplete.")
    elif score < 80:
        verdict = DesignVerdict.NEEDS_REVISION
        reasons.append("Design quality score is below the approval threshold of 80.")
    else:
        verdict = DesignVerdict.PASS
        reasons.append("Design satisfies the governed-design approval threshold.")

    return DesignAssessment(
        proposal_id=proposal.proposal_id,
        verdict=verdict,
        score=score,
        reasons=tuple(reasons),
        missing_evidence=tuple(missing_evidence),
        invariant_failures=tuple(invariant_failures),
        principles=principles,
    )
