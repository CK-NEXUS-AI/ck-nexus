"""Tests for CK-NEXUS personal intelligence contracts."""

from datetime import UTC, datetime, timedelta

import pytest

from creator_app.personal_intelligence import (
    ConsentLedger,
    ConsentRequired,
    PersonalCapability,
    PersonaPreferences,
    SemanticMemoryStore,
    UserPreferenceProfile,
    build_audit_event,
    choose_response_style,
    estimate_tone,
)


def test_consent_is_denied_by_default() -> None:
    ledger = ConsentLedger()
    assert ledger.allowed(PersonalCapability.GMAIL_READ) is False
    with pytest.raises(ConsentRequired):
        ledger.require(PersonalCapability.GMAIL_READ)


def test_consent_can_be_granted_and_revoked() -> None:
    ledger = ConsentLedger()
    ledger.grant(PersonalCapability.GMAIL_READ, purpose="summarize selected inbox messages")
    assert ledger.allowed(PersonalCapability.GMAIL_READ) is True
    assert ledger.revoke(PersonalCapability.GMAIL_READ) is True
    assert ledger.allowed(PersonalCapability.GMAIL_READ) is False


def test_expired_consent_is_denied() -> None:
    ledger = ConsentLedger()
    ledger.grant(
        PersonalCapability.PROFILE_LEARN,
        purpose="learn response preferences",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert ledger.allowed(PersonalCapability.PROFILE_LEARN) is False


def test_explicit_preference_does_not_require_inference_consent() -> None:
    profile = UserPreferenceProfile(ConsentLedger())
    item = profile.set_explicit("response_length", "short")
    assert item.confidence == 1.0
    assert profile.get("response_length") == item


def test_inferred_preference_requires_consent() -> None:
    profile = UserPreferenceProfile(ConsentLedger())
    with pytest.raises(ConsentRequired):
        profile.learn("response_length", "short", confidence=0.8, source="chat_pattern")


def test_inferred_sensitive_attribute_is_rejected() -> None:
    ledger = ConsentLedger()
    ledger.grant(PersonalCapability.PROFILE_LEARN, purpose="learn response preferences")
    profile = UserPreferenceProfile(ledger)
    with pytest.raises(ValueError, match="sensitive"):
        profile.learn("religion", "example", confidence=0.9, source="chat_pattern")


def test_memory_requires_explicit_consent() -> None:
    store = SemanticMemoryStore(ConsentLedger())
    with pytest.raises(ConsentRequired):
        store.remember(category="preference", summary="Prefers concise answers", source="chat")


def test_memory_is_minimized_and_deletable() -> None:
    ledger = ConsentLedger()
    ledger.grant(PersonalCapability.MEMORY_STORE, purpose="remember explicit preferences")
    store = SemanticMemoryStore(ledger)
    item = store.remember(
        category="preference",
        summary="  Prefers   concise answers  ",
        source="explicit_user_statement",
    )
    assert item.summary == "Prefers concise answers"
    assert store.delete(item.memory_id) is True
    assert store.active() == ()


def test_memory_rejects_oversized_summary() -> None:
    ledger = ConsentLedger()
    ledger.grant(PersonalCapability.MEMORY_STORE, purpose="remember explicit preferences")
    store = SemanticMemoryStore(ledger)
    with pytest.raises(ValueError, match="1-500"):
        store.remember(category="preference", summary="x" * 501, source="chat")


def test_tone_estimate_is_transient_and_non_diagnostic() -> None:
    estimate = estimate_tone("วันนี้เหนื่อยและกังวลนิดหน่อย")
    assert estimate.label == "concerned"
    assert estimate.persistent is False
    assert estimate.diagnostic is False
    assert estimate.confidence <= 0.65


def test_persona_never_claims_human_identity_or_real_emotions() -> None:
    style = choose_response_style(PersonaPreferences(), estimate_tone("ขอบคุณ ดีมาก"))
    assert style.transparent_ai is True
    assert style.claim_real_emotions is False
    assert style.imitate_human_identity is False


def test_concerned_tone_disables_humor() -> None:
    style = choose_response_style(PersonaPreferences(humor="light"), estimate_tone("ผมกังวลมาก"))
    assert style.warmth == "supportive"
    assert style.humor == "none"


def test_audit_event_stores_digest_not_raw_content() -> None:
    raw = b"private message body"
    event = build_audit_event(
        action="analyze",
        capability="gmail.read",
        decision="ALLOW",
        purpose="summarize selected message",
        resource_ref="gmail:message:opaque-id",
        content=raw,
    )
    assert event.content_digest is not None
    assert event.raw_content_stored is False
    assert "private message body" not in repr(event)


def test_snapshot_does_not_include_secret_material() -> None:
    ledger = ConsentLedger()
    ledger.grant(PersonalCapability.CROSS_CHANNEL_SYNC, purpose="sync authorized context")
    snapshot = ledger.snapshot()
    assert snapshot["cross_channel.sync"]["allowed"] is True
    assert "token" not in str(snapshot).lower()
