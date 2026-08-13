from __future__ import annotations

import pytest

from creator_app.credential_broker import (
    CredentialAccessDenied,
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)


def test_broker_enforces_consumer_policy_and_redacts_repr() -> None:
    broker = CredentialBroker(environment={CredentialId.OPENAI_API_KEY: "sk-test-secret"})
    lease = broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")

    assert lease.reveal(consumer="provider.openai") == "sk-test-secret"
    assert "sk-test-secret" not in repr(lease)
    assert "redacted" in repr(lease)
    with pytest.raises(CredentialAccessDenied):
        lease.reveal(consumer="gmail.oauth")
    with pytest.raises(CredentialAccessDenied):
        broker.acquire(CredentialId.OPENAI_API_KEY, consumer="gmail.oauth")


def test_ephemeral_secret_overrides_environment_and_can_expire(monkeypatch) -> None:
    broker = CredentialBroker(environment={CredentialId.GMAIL_ACCESS_TOKEN: "env-token"})
    broker.put_ephemeral(
        CredentialId.GMAIL_ACCESS_TOKEN,
        "runtime-token",
        source="oauth",
        ttl_seconds=60,
    )
    lease = broker.acquire(CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api")
    assert lease.reveal(consumer="gmail.api") == "runtime-token"
    status = broker.statuses(consumer="gmail.api")
    assert any(
        item.ephemeral for item in status if item.credential_id == CredentialId.GMAIL_ACCESS_TOKEN
    )


def test_missing_allowed_credential_is_safe() -> None:
    broker = CredentialBroker()
    with pytest.raises(CredentialUnavailable, match="not configured"):
        broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")
