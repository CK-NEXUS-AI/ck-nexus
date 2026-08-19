"""Tests for capability execution and Trusted Verifier V2 lifecycle."""

from datetime import UTC, datetime, timedelta

import pytest

from creator_app.execution_fabric_v2 import (
    CapabilityLease,
    ExecutionAction,
    ExecutionDenied,
    ExecutionPolicyBroker,
    ExecutionProposal,
)
from creator_app.trusted_verifier_v2 import (
    PROFILE_POLICIES,
    TrustedVerifierEntry,
    TrustedVerifierRegistry,
    VerifierProfile,
    VerifierState,
    VerifierTrustDenied,
    policy_for,
)


def _lease(
    *,
    capability: str = "github.patch.create",
    scope: str = "repo:ck-nexus",
    max_actions: int = 1,
    domains: frozenset[str] = frozenset({"api.github.com"}),
    release_authorized: bool = False,
) -> CapabilityLease:
    return CapabilityLease(
        lease_id="lease-test-001",
        capability=capability,
        scope=scope,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        max_actions=max_actions,
        network_domains=domains,
        credential_refs=("cred://github/app/default",),
        release_authorized=release_authorized,
    )


def _entry(
    image_hex: str,
    *,
    profile: VerifierProfile = VerifierProfile.PYTHON_QUALITY,
) -> TrustedVerifierEntry:
    policy = policy_for(profile)
    return TrustedVerifierEntry(
        image_ref="ghcr.io/example/verifier@sha256:" + image_hex * 64,
        source_commit="a" * 40,
        entrypoint_digest="b" * 64,
        policy_digest=policy.digest,
        sbom_digest="c" * 64,
        build_provenance_digest="d" * 64,
        profile=profile,
    )


def test_capability_lease_rejects_wildcard_network_and_raw_credentials() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        CapabilityLease(
            lease_id="lease-x",
            capability="x",
            scope="x",
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
            network_domains=frozenset({"*"}),
        )
    with pytest.raises(ValueError, match="cred://"):
        CapabilityLease(
            lease_id="lease-y",
            capability="x",
            scope="x",
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
            credential_refs=("raw-secret-value",),
        )


def test_broker_enforces_exact_capability_scope_and_domain() -> None:
    broker = ExecutionPolicyBroker()
    lease = _lease(max_actions=3)
    with pytest.raises(ExecutionDenied, match="capability"):
        broker.authorize(
            ExecutionProposal(
                ExecutionAction.PATCH_CREATE,
                "other",
                "repo:ck-nexus",
            ),
            lease,
        )
    with pytest.raises(ExecutionDenied, match="destination"):
        broker.authorize(
            ExecutionProposal(
                ExecutionAction.PATCH_CREATE,
                "github.patch.create",
                "repo:ck-nexus",
                destination_domain="evil.example",
            ),
            lease,
        )
    receipt = broker.authorize(
        ExecutionProposal(
            ExecutionAction.PATCH_CREATE,
            "github.patch.create",
            "repo:ck-nexus",
            destination_domain="api.github.com",
        ),
        lease,
    )
    assert receipt.allowed is True
    assert receipt.credential_refs == ("cred://github/app/default",)


def test_broker_consumes_bounded_action_budget() -> None:
    broker = ExecutionPolicyBroker()
    lease = _lease(max_actions=1)
    proposal = ExecutionProposal(
        ExecutionAction.PATCH_CREATE,
        "github.patch.create",
        "repo:ck-nexus",
    )
    broker.authorize(proposal, lease)
    assert broker.remaining_actions(lease) == 0
    with pytest.raises(ExecutionDenied, match="budget exhausted"):
        broker.authorize(proposal, lease)


def test_external_write_and_production_mutation_are_fail_closed() -> None:
    broker = ExecutionPolicyBroker()
    write_lease = _lease(capability="gmail.send", scope="mailbox:me", max_actions=2)
    with pytest.raises(ExecutionDenied, match="explicit user approval"):
        broker.authorize(
            ExecutionProposal(ExecutionAction.EXTERNAL_WRITE, "gmail.send", "mailbox:me"),
            write_lease,
        )
    write_receipt = broker.authorize(
        ExecutionProposal(
            ExecutionAction.EXTERNAL_WRITE,
            "gmail.send",
            "mailbox:me",
            user_approved=True,
        ),
        write_lease,
    )
    assert write_receipt.allowed is True

    prod_lease = _lease(
        capability="deploy.production",
        scope="service:ck-nexus",
        release_authorized=False,
    )
    with pytest.raises(ExecutionDenied, match="release-authorized"):
        broker.authorize(
            ExecutionProposal(
                ExecutionAction.PRODUCTION_MUTATION,
                "deploy.production",
                "service:ck-nexus",
                user_approved=True,
            ),
            prod_lease,
        )


def test_patch_creation_cannot_escape_patch_only_contract() -> None:
    with pytest.raises(ExecutionDenied, match="patch-only"):
        ExecutionPolicyBroker().authorize(
            ExecutionProposal(
                ExecutionAction.PATCH_CREATE,
                "github.patch.create",
                "repo:ck-nexus",
                patch_only=False,
            ),
            _lease(),
        )


def test_verifier_registry_requires_explicit_active_trust_tuple() -> None:
    registry = TrustedVerifierRegistry()
    entry = _entry("1")
    registry.register(entry)
    with pytest.raises(VerifierTrustDenied, match="not active"):
        registry.require_active(
            image_ref=entry.image_ref,
            profile=entry.profile,
            policy_digest=entry.policy_digest,
        )
    registry.transition(entry.image_ref, entry.profile, VerifierState.ACTIVE)
    accepted = registry.require_active(
        image_ref=entry.image_ref,
        profile=entry.profile,
        policy_digest=entry.policy_digest,
    )
    assert accepted.state == VerifierState.ACTIVE
    with pytest.raises(VerifierTrustDenied, match="policy digest"):
        registry.require_active(
            image_ref=entry.image_ref,
            profile=entry.profile,
            policy_digest="f" * 64,
        )


def test_verifier_rotation_deprecates_previous_and_revocation_is_terminal() -> None:
    registry = TrustedVerifierRegistry()
    first = _entry("1")
    second = _entry("2")
    registry.register(first)
    registry.register(second)
    registry.transition(first.image_ref, first.profile, VerifierState.ACTIVE)
    registry.transition(second.image_ref, second.profile, VerifierState.ACTIVE)
    assert registry.active(first.profile).image_ref == second.image_ref
    registry.revoke(second.image_ref, second.profile)
    assert registry.active(second.profile) is None
    with pytest.raises(VerifierTrustDenied, match="cannot be reactivated"):
        registry.transition(second.image_ref, second.profile, VerifierState.ACTIVE)


def test_all_v2_profiles_deny_network_credentials_and_host_execution_by_default() -> None:
    assert set(PROFILE_POLICIES) == set(VerifierProfile)
    for policy in PROFILE_POLICIES.values():
        assert policy.network == "deny"
        assert policy.credentials == "deny"
        assert policy.host_execution is False
        assert len(policy.digest) == 64
