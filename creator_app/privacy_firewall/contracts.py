"""Privacy and trust contracts for CK-NEXUS data movement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    SECRET = "secret"
    REGULATED = "regulated"


class TrustLevel(StrEnum):
    AUTHORITATIVE = "authoritative"
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


@dataclass(frozen=True, slots=True)
class ContentEnvelope:
    """Content plus provenance and taint that follows it through the pipeline."""

    source: str
    content: str
    classification: DataClassification = DataClassification.INTERNAL
    trust: TrustLevel = TrustLevel.UNTRUSTED
    purpose: str = "unspecified"
    taints: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.purpose.strip():
            raise ValueError("purpose must not be empty")


@dataclass(frozen=True, slots=True)
class PrivacyPolicy:
    """Disclosure boundary for one processing request."""

    external_allowed: bool = False
    personal_external_consent: bool = False
    sensitive_external_consent: bool = False
    regulated_external_consent: bool = False
    prefer_local: bool = True


@dataclass(frozen=True, slots=True)
class RedactionResult:
    content: str
    redaction_count: int
    detected_classes: frozenset[DataClassification]
    taints: frozenset[str]


@dataclass(frozen=True, slots=True)
class DisclosureDecision:
    allowed: bool
    destination: str
    reason: str
    classification: DataClassification
    redacted_content: str
    evidence: dict[str, object]
