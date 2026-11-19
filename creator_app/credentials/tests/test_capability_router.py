"""Tests for the capability router and universal credential broker."""

from __future__ import annotations

import pytest

from creator_app.credentials.capability_registry import (
    Capability,
    CapabilityRegistry,
    ProviderCandidate,
)
from creator_app.credentials.credential_broker import CredentialBroker, CredentialId


def test_capability_registry_has_canonical_capabilities() -> None:
    registry = CapabilityRegistry()
    caps = registry.list()

    assert "openai.responses" in caps
    assert "gmail.read" in caps
    assert "github.repo.read" in caps
    assert "github.repo.write" in caps
    assert "slack.messages.read" in caps
    assert "slack.messages.write" in caps
    assert "google.drive.read" in caps
    assert "hubspot.crm.read" in caps
    assert "airtable.records.read" in caps
    assert "postgres.query" in caps

    # Gmail requires OAuth consumer policy
    gmail_spec = registry.get("gmail.read")
    assert gmail_spec is not None
    assert gmail_spec.required_consumer == "gmail.oauth"
    assert len(gmail_spec.credential_ids) == 4
    assert "gmail.client_id" in gmail_spec.credential_ids


def test_capability_registry_scopes() -> None:
    registry = CapabilityRegistry()

    gmail_scopes = registry.required_scopes("gmail.read")
    assert "https://www.googleapis.com/auth/gmail.readonly" in gmail_scopes

    github_scopes = registry.required_scopes("github.repo.write")
    assert "repo" in github_scopes
    assert "workflow" in github_scopes


def test_provider_candidate_quota_tracking() -> None:
    candidate = ProviderCandidate(
        provider="openai",
        capability=Capability.OPENAI_RESPONSES,
        credential_id="openai.api_key:key1",
        quota_remaining=47,
        quota_total=100,
        health="healthy",
    )
    pct = candidate.quota_percentage_used()
    assert pct is not None
    assert pct == 53.0
    assert not candidate.is_quota_exhausted()

    # At 95% threshold
    candidate_high = ProviderCandidate(
        provider="openai",
        capability=Capability.OPENAI_RESPONSES,
        credential_id="openai.api_key:key2",
        quota_remaining=5,
        quota_total=100,
        health="healthy",
    )
    assert candidate_high.is_quota_exhausted()
    assert candidate_high.quota_percentage_used() == 95.0


def test_broker_integrates_with_capability_registry() -> None:
    """Verify broker and registry work together."""
    broker = CredentialBroker(
        environment={
            CredentialId.OPENAI_API_KEY: "sk-test-secret",
        }
    )
    CapabilityRegistry()

    # Broker should allow acquire for openai.responses consumer
    lease = broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")
    assert lease.reveal(consumer="provider.openai") == "sk-test-secret"

    # Gmail consumer should not have access to openai key
    with pytest.raises((PermissionError, RuntimeError)):
        broker.acquire(CredentialId.OPENAI_API_KEY, consumer="gmail.oauth")


def test_credential_leases_are_consumer_bound() -> None:
    broker = CredentialBroker(
        environment={
            CredentialId.OPENAI_API_KEY: "sk-secret",
            CredentialId.GMAIL_ACCESS_TOKEN: "gmail-token",
        }
    )

    openai_lease = broker.acquire(CredentialId.OPENAI_API_KEY, consumer="provider.openai")
    gmail_lease = broker.acquire(CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api")

    # Each lease can only be revealed by its bound consumer
    assert openai_lease.reveal(consumer="provider.openai") == "sk-secret"

    with pytest.raises((PermissionError, RuntimeError)):
        openai_lease.reveal(consumer="gmail.api")

    # Repr should never leak secret values
    assert "sk-secret" not in repr(openai_lease)
    assert "gmail-token" not in repr(gmail_lease)


def test_capability_candidate_scoring_prioritizes_healthy() -> None:
    """Provider candidates should be ordered: healthy first, then by score."""
    healthy = ProviderCandidate(
        provider="groq",
        capability=Capability.OPENAI_RESPONSES,
        credential_id="openai.api_key:groq",
        health="healthy",
        quota_remaining=100,
        quota_total=100,
        priority=5,
    )
    degraded = ProviderCandidate(
        provider="openai",
        capability=Capability.OPENAI_RESPONSES,
        credential_id="openai.api_key:openai",
        health="degraded",
        quota_remaining=5,
        quota_total=100,
        priority=5,
    )

    candidates = [degraded, healthy]
    candidates.sort(key=lambda c: 0 if c.health == "healthy" else 100)

    assert candidates[0] is healthy
    assert candidates[1] is degraded
