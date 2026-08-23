from __future__ import annotations

from dataclasses import dataclass

from .catalog import KnowledgeCatalog
from .models import AdoptionMode, KnowledgeItem, KnowledgeStatus, SearchDecision


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    problem_key: str
    attempts: int
    last_reason: str = ""


def predevelopment_search(catalog: KnowledgeCatalog, query: str) -> SearchDecision:
    matches = catalog.search(query)
    reusable = tuple(
        item
        for item in matches
        if item.status in {KnowledgeStatus.ADOPTABLE, KnowledgeStatus.ADOPTED}
        and item.adoption_mode in {AdoptionMode.ADOPT, AdoptionMode.WRAP}
    )
    if reusable:
        return SearchDecision(
            query=query,
            matches=reusable,
            build_new_allowed=False,
            reason="Reusable adoptable or wrappable capability exists. Adapt before building new.",
        )
    return SearchDecision(
        query=query,
        matches=matches,
        build_new_allowed=True,
        reason="No adoptable or wrappable match is recorded. New work requires evidence and review.",
    )


def enforce_two_strike(record: AttemptRecord) -> str:
    if record.attempts < 0:
        raise ValueError("attempts must be non-negative")
    if record.attempts >= 2:
        return "stop_and_research"
    return "continue_bounded_attempt"


def best_capability_matches(
    catalog: KnowledgeCatalog,
    required_capabilities: set[str],
) -> tuple[KnowledgeItem, ...]:
    required = {value.casefold() for value in required_capabilities}
    scored: list[tuple[int, KnowledgeItem]] = []
    for item in catalog.all():
        available = {value.casefold() for value in item.capabilities}
        score = len(required & available)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1].item_id))
    return tuple(item for _, item in scored)
