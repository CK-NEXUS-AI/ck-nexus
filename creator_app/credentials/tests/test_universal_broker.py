"""Integration tests for the Universal Credential Broker system."""

from __future__ import annotations

import os

import pytest

from creator_app.credentials.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)
from creator_app.credentials.llm_keypool import LlmKeyPool, LlmKeySpec


def test_full_system_integration() -> None:
    """Verify the full credential broker + keypool + capability registry chain works."""
    # Setup environment
    os.environ["GROQ_API_KEY"] = "gsk_test_key"
    os.environ["OPENAI_API_KEY"] = "sk_test_key"

    # Broker with environment credentials
    broker = CredentialBroker.from_environment()
    statuses = broker.statuses(consumer="provider.openai")
    assert any(s.configured for s in statuses if s.credential_id == CredentialId.OPENAI_API_KEY)

    # KeyPool auto-discovers from environment
    pool = LlmKeyPool.from_environment()
    assert pool is not None
    assert len(pool.specs) >= 1

    # Acquire a key
    selection = pool.acquire()
    if selection is not None:
        assert selection.api_key
        assert selection.api_key == "gsk_test_key" or selection.api_key == "sk_test_key"

    # Clean up
    for key in ("GROQ_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(key, None)


def test_fail_closed_when_no_credentials() -> None:
    """System should fail closed when no credentials are available."""
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)

    broker = CredentialBroker()

    with pytest.raises(CredentialUnavailable):
        broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")

    pool = LlmKeyPool.from_environment()
    assert pool is None  # No keys configured


def test_capability_registry_integration() -> None:
    """Verify capability registry integrates with credential broker."""
    os.environ["GOOGLE_CLIENT_ID"] = "test_client_id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test_client_secret"
    os.environ["GOOGLE_REFRESH_TOKEN"] = "test_refresh_token"

    broker = CredentialBroker.from_environment()
    broker.put_ephemeral(
        CredentialId.GMAIL_CLIENT_ID,
        "env_client_id",
        source="env",
        ttl_seconds=3600,
    )

    statuses = broker.statuses(consumer="gmail.oauth")
    credential_ids = [s.credential_id for s in statuses]
    assert "gmail.client_id" in credential_ids

    os.environ.pop("GOOGLE_CLIENT_ID", None)
    os.environ.pop("GOOGLE_CLIENT_SECRET", None)
    os.environ.pop("GOOGLE_REFRESH_TOKEN", None)


def test_state_persistence(tmp_path) -> None:
    """Verify key pool state persists to disk across restarts."""
    state_file = tmp_path / "key_pool_state.json"

    os.environ["TEST_STATE_KEY"] = "sk-test"

    specs = [
        LlmKeySpec(
            id="test-key",
            env_var="TEST_STATE_KEY",
            base_url="https://api.test.com/v1",
            model="gpt-4",
        )
    ]

    pool1 = LlmKeyPool(specs, state_path=str(state_file))
    pool1.report_failure("test-key", status_code=401)

    # State should be saved
    assert state_file.exists()

    # New pool instance should load state
    pool2 = LlmKeyPool(specs, state_path=str(state_file))
    statuses = pool2.status()
    test_status = next(s for s in statuses if s.key_id == "test-key")
    assert test_status.exhausted is True

    os.environ.pop("TEST_STATE_KEY", None)


def test_quota_warning_threshold_is_configurable() -> None:
    """The 95% threshold should be configurable."""
    os.environ["TEST_Q_KEY"] = "sk-test"

    specs = [
        LlmKeySpec(
            id="test-q", env_var="TEST_Q_KEY", base_url="https://api.test.com/v1", model="gpt-4"
        )
    ]

    pool = LlmKeyPool(specs, quota_warning_threshold_pct=80.0)
    pool.report_quota_usage(key_id="test-q", used=85, total=100)

    statuses = pool.status()
    key_status = next(s for s in statuses if s.key_id == "test-q")
    assert key_status.exhausted is True
    assert key_status.quota_percentage_used == 85.0

    os.environ.pop("TEST_Q_KEY", None)
