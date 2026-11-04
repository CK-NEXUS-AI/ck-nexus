from __future__ import annotations

from datetime import UTC, datetime

import pytest

from creator_app.search_control_fabric import (
    ControlActionContract,
    ControlActionRequest,
    ControlRisk,
    DiscoveryDisposition,
    DiscoverySource,
    RightsBasis,
    SourceTrust,
    assess_discovery_source,
    authorize_control_action,
)


def source(**overrides):
    values = {
        "source_id": "official-docs",
        "url": "https://example.com/docs",
        "publisher": "Example",
        "fetched_at": "2026-11-01T00:00:00Z",
        "content_sha256": "a" * 64,
        "rights_basis": RightsBasis.OPEN_LICENSE,
        "license_id": "CC-BY-4.0",
        "rights_evidence_ref": "license-record:1",
        "trust": SourceTrust.OFFICIAL,
    }
    values.update(overrides)
    return DiscoverySource(**values)


def test_verified_source_requires_known_rights_and_trust():
    now = datetime(2026, 11, 1, 1, tzinfo=UTC)
    assert assess_discovery_source(source(), now=now) is DiscoveryDisposition.VERIFIED_CANDIDATE
    assert (
        assess_discovery_source(source(rights_basis=RightsBasis.UNKNOWN, license_id=None), now=now)
        is DiscoveryDisposition.DISCOVERY_ONLY
    )
    assert (
        assess_discovery_source(source(trust=SourceTrust.UNVERIFIED), now=now)
        is DiscoveryDisposition.DISCOVERY_ONLY
    )


def test_stale_or_future_source_is_not_usable():
    now = datetime(2026, 11, 1, 0, tzinfo=UTC)
    assert (
        assess_discovery_source(source(fetched_at="2026-01-01T00:00:00Z"), now=now)
        is DiscoveryDisposition.STALE
    )
    assert (
        assess_discovery_source(source(fetched_at="2026-11-01T01:00:00Z"), now=now)
        is DiscoveryDisposition.BLOCKED
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": "http://example.com"},
        {"url": "https://user:secret@example.com"},
        {"content_sha256": "not-a-hash"},
        {"fetched_at": "2026-11-01T00:00:00"},
        {"rights_basis": RightsBasis.OPEN_LICENSE, "license_id": None},
        {"rights_evidence_ref": None},
    ],
)
def test_invalid_source_provenance_is_rejected(overrides):
    with pytest.raises(ValueError):
        source(**overrides)


def test_official_source_content_is_still_untrusted_instruction():
    assert source().instructions_trusted is False


def test_read_action_requires_exact_identity_scope_and_bounded_timeout():
    contract = ControlActionContract(
        "github", "list_repositories", frozenset({"github.read"}), ControlRisk.READ
    )
    request = ControlActionRequest(
        "github", "list_repositories", "owner:1", frozenset({"github.read"})
    )
    assert not authorize_control_action(contract, request, grant_verifier=None).allowed
    decision = authorize_control_action(contract, request, grant_verifier=lambda **_: True)
    assert decision.allowed is True
    assert decision.execution_performed is False
    assert decision.authority_level == "NONE"

    mismatch = ControlActionRequest(
        "github", "delete_repository", "owner:1", frozenset({"github.read"})
    )
    assert not authorize_control_action(contract, mismatch, grant_verifier=None).allowed


def test_write_action_fails_closed_without_idempotency_approval_and_core_grant():
    contract = ControlActionContract(
        "magento",
        "update_product",
        frozenset({"magento.product.write"}),
        ControlRisk.CONTROLLED_WRITE,
    )
    base = dict(
        connector_id="magento",
        action_id="update_product",
        principal_id="owner:1",
        granted_scopes=frozenset({"magento.product.write"}),
    )
    assert (
        authorize_control_action(
            contract, ControlActionRequest(**base), grant_verifier=lambda **_: True
        ).reason
        == "idempotency_key_required"
    )

    request = ControlActionRequest(**base, idempotency_key="job:123", approval_ref="approval:123")
    assert not authorize_control_action(contract, request, grant_verifier=None).allowed
    assert not authorize_control_action(contract, request, grant_verifier=lambda **_: False).allowed
    assert authorize_control_action(contract, request, grant_verifier=lambda **_: True).allowed


def test_destructive_action_requires_separate_owner_approval():
    contract = ControlActionContract(
        "cloudways",
        "delete_instance",
        frozenset({"cloudways.instance.delete"}),
        ControlRisk.DESTRUCTIVE,
    )
    base = dict(
        connector_id="cloudways",
        action_id="delete_instance",
        principal_id="owner:1",
        granted_scopes=frozenset({"cloudways.instance.delete"}),
        idempotency_key="job:delete-1",
        approval_ref="policy:grant-1",
    )
    assert (
        authorize_control_action(
            contract, ControlActionRequest(**base), grant_verifier=lambda **_: True
        ).reason
        == "owner_approval_required"
    )
    approved = ControlActionRequest(**base, owner_approval_ref="owner:attestation-1")
    assert authorize_control_action(contract, approved, grant_verifier=lambda **_: True).allowed


def test_grant_verifier_exception_denies_without_execution():
    contract = ControlActionContract(
        "n8n", "activate_workflow", frozenset({"n8n.workflow.write"}), ControlRisk.SANDBOX_WRITE
    )
    request = ControlActionRequest(
        "n8n",
        "activate_workflow",
        "owner:1",
        frozenset({"n8n.workflow.write"}),
        idempotency_key="job:1",
        approval_ref="approval:1",
    )
    decision = authorize_control_action(
        contract,
        request,
        grant_verifier=lambda **_: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    assert not decision.allowed
    assert decision.reason == "trusted_grant_verification_failed"
    assert decision.execution_performed is False


def test_candidate_requires_source_and_evidence_lineage():
    from creator_app.search_control_fabric import DiscoveryCandidate

    candidate = DiscoveryCandidate(
        candidate_id="candidate:1",
        source_id="official-docs",
        capability="workflow-automation",
        title="Workflow API",
        summary="Official API reference for workflow management.",
        observed_at="2026-11-01T00:00:00Z",
        evidence_ref="sha256:abc123",
    )
    assert candidate.source_id == "official-docs"
    with pytest.raises(ValueError, match="evidence_ref"):
        DiscoveryCandidate(
            candidate_id="candidate:2",
            source_id="official-docs",
            capability="workflow-automation",
            title="Workflow API",
            summary="Official API reference.",
            observed_at="2026-11-01T00:00:00Z",
            evidence_ref="",
        )


def test_write_action_rejects_missing_scope_and_excessive_timeout():
    contract = ControlActionContract(
        "magento",
        "update_product",
        frozenset({"magento.product.write"}),
        ControlRisk.CONTROLLED_WRITE,
        max_timeout_seconds=20,
    )
    request = ControlActionRequest(
        "magento",
        "update_product",
        "owner:1",
        frozenset({"magento.read"}),
        timeout_seconds=21,
        idempotency_key="job:1",
        approval_ref="approval:1",
    )
    decision = authorize_control_action(contract, request, grant_verifier=lambda **_: True)
    assert decision.reason == "required_scope_missing"
