from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class KnowledgeStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    STUDYING = "studying"
    UNDERSTOOD = "understood"
    ADOPTABLE = "adoptable"
    ADOPTED = "adopted"
    REJECTED = "rejected"


class EvidenceLevel(StrEnum):
    UNVERIFIED = "unverified"
    DOCUMENTED = "documented"
    TESTED = "tested"
    VERIFIED = "verified"


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    source_id: str
    name: str
    url: str
    source_type: str
    discovered_at: datetime
    license_name: str | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.UNVERIFIED
    notes: str = ""


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    item_id: str
    name: str
    category: str
    summary: str
    usage: str
    status: KnowledgeStatus
    sources: tuple[KnowledgeSource, ...]
    relevance: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    tags: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class SearchDecision:
    query: str
    matches: tuple[KnowledgeItem, ...]
    build_new_allowed: bool
    reason: str


def utc_now() -> datetime:
    return datetime.now(UTC)
