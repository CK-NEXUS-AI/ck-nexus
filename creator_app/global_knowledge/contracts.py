"""Canonical contracts for global knowledge discovery.

The contracts preserve provenance and uncertainty. Derived claims are never
silently promoted to verified facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DiscoveryMode(StrEnum):
    BROAD = "broad"
    DEEP = "deep"
    REACTIVE = "reactive"
    REFRESH = "refresh"


class SourceKind(StrEnum):
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    NEWS = "news"
    INDUSTRY = "industry"
    WIKI = "wiki"
    COMMUNITY = "community"
    SOCIAL = "social"
    PUBLIC_DOCUMENT = "public_document"
    STRUCTURED_DATA = "structured_data"
    OTHER = "other"


class Reliability(StrEnum):
    OBSERVED = "observed"
    MEASURED = "measured"
    DERIVED = "derived"
    INFERRED = "inferred"
    USER_PROVIDED = "user_provided"
    VERIFIED = "verified"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_id: str
    url: str
    canonical_url: str
    source_kind: SourceKind
    language: str
    region: str
    observed_at: str
    content_hash: str
    published_at: str | None = None
    author: str | None = None
    title: str | None = None
    license_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("source URL must be http(s)")
        if not self.content_hash.strip():
            raise ValueError("content_hash is required for provenance")


@dataclass(frozen=True, slots=True)
class EntityRef:
    entity_id: str
    entity_type: str
    canonical_name: str
    aliases: tuple[str, ...] = ()
    external_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Relation:
    relation_id: str
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    source_ids: tuple[str, ...]
    confidence: float
    reliability: Reliability
    observed_at: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")
        if not self.source_ids:
            raise ValueError("relations require provenance source_ids")


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    subject: str
    predicate: str
    object_value: str
    source_ids: tuple[str, ...]
    confidence: float
    reliability: Reliability
    observed_at: str
    valid_from: str | None = None
    valid_to: str | None = None
    qualifiers: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")
        if not self.source_ids:
            raise ValueError("claims require provenance source_ids")


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str
    mode: DiscoveryMode = DiscoveryMode.REACTIVE
    languages: tuple[str, ...] = ("th", "en")
    regions: tuple[str, ...] = ("asia", "global")
    source_kinds: tuple[SourceKind, ...] = ()
    max_sources: int = 40
    freshness_seconds: int | None = None
    require_original_language: bool = True

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query is required")
        if self.max_sources < 1:
            raise ValueError("max_sources must be positive")
