"""Privacy-first preference learning for CK-NEXUS."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .consent import ConsentLedger, PersonalCapability

_SENSITIVE_KEYS = frozenset(
    {
        "health_status",
        "religion",
        "sexual_orientation",
        "political_affiliation",
        "biometric_identity",
        "precise_location",
    }
)


@dataclass(frozen=True, slots=True)
class Preference:
    key: str
    value: str
    confidence: float
    source: str
    learned_at: datetime
    persistent: bool


class UserPreferenceProfile:
    """Stores explicit preferences and consent-gated non-sensitive inferences."""

    def __init__(self, consent: ConsentLedger) -> None:
        self._consent = consent
        self._items: dict[str, Preference] = {}

    def set_explicit(self, key: str, value: str) -> Preference:
        normalized_key = self._validate_key(key)
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("preference value must not be empty")
        item = Preference(
            key=normalized_key,
            value=normalized_value,
            confidence=1.0,
            source="explicit_user_statement",
            learned_at=datetime.now(UTC),
            persistent=True,
        )
        self._items[normalized_key] = item
        return item

    def learn(
        self,
        key: str,
        value: str,
        *,
        confidence: float,
        source: str,
    ) -> Preference:
        self._consent.require(PersonalCapability.PROFILE_LEARN)
        normalized_key = self._validate_key(key)
        if normalized_key in _SENSITIVE_KEYS:
            raise ValueError("sensitive attributes are not inferred by this profile engine")
        normalized_value = value.strip()
        normalized_source = source.strip()
        if not normalized_value or not normalized_source:
            raise ValueError("inferred preference value/source must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        item = Preference(
            key=normalized_key,
            value=normalized_value,
            confidence=confidence,
            source=normalized_source,
            learned_at=datetime.now(UTC),
            persistent=True,
        )
        self._items[normalized_key] = item
        return item

    def get(self, key: str) -> Preference | None:
        return self._items.get(key.strip().lower())

    def delete(self, key: str) -> bool:
        return self._items.pop(key.strip().lower(), None) is not None

    def export(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for key, item in sorted(self._items.items()):
            payload = asdict(item)
            payload["learned_at"] = item.learned_at.isoformat()
            result[key] = payload
        return result

    @staticmethod
    def _validate_key(key: str) -> str:
        normalized = key.strip().lower()
        if not normalized or len(normalized) > 80:
            raise ValueError("preference key must be 1-80 characters")
        return normalized
