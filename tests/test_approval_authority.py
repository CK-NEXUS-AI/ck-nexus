from __future__ import annotations

import pytest

from creator_app.approval_authority import ApprovalAuthority


class FakeVerifier:
    def __init__(self, accepted: str = "ok") -> None:
        self.accepted = accepted

    def verify(self, *, challenge: str, assertion: str, actor_id: str) -> bool:
        return bool(challenge and actor_id) and assertion == self.accepted


def authority() -> ApprovalAuthority:
    return ApprovalAuthority(signing_key=b"k" * 32, verifier=FakeVerifier())


def challenge(a: ApprovalAuthority):
    return a.create_challenge(
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
    )


def test_challenge_is_opaque_and_bounded():
    a = authority()
    c = challenge(a)
    assert c.challenge_id.startswith("apc_")
    assert "gemini" not in c.challenge
    with pytest.raises(ValueError):
        a.create_challenge(
            actor_id="u", action="a", resource="r", fingerprint="f", ttl_seconds=301
        )


def test_successful_assertion_produces_scoped_signed_token():
    a = authority()
    c = challenge(a)
    approval = a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")
    payload = a.redeem(
        approval.token,
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
    )
    assert payload["approval_id"] == approval.approval_id
    assert "ok" not in approval.token


def test_challenge_is_one_time_even_after_failed_assertion():
    a = authority()
    c = challenge(a)
    with pytest.raises(PermissionError):
        a.complete_challenge(challenge_id=c.challenge_id, assertion="wrong")
    with pytest.raises(PermissionError):
        a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")


def test_token_is_one_time_and_scope_bound():
    a = authority()
    c = challenge(a)
    approval = a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")
    with pytest.raises(PermissionError):
        a.redeem(
            approval.token,
            actor_id="user-1",
            action="provider.authorize",
            resource="provider:claude",
            fingerprint="f" * 64,
        )
    a.redeem(
        approval.token,
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
    )
    with pytest.raises(PermissionError):
        a.redeem(
            approval.token,
            actor_id="user-1",
            action="provider.authorize",
            resource="provider:gemini",
            fingerprint="f" * 64,
        )


def test_tampered_token_fails_closed():
    a = authority()
    c = challenge(a)
    approval = a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")
    bad = approval.token[:-1] + ("A" if approval.token[-1] != "A" else "B")
    with pytest.raises(PermissionError):
        a.redeem(
            bad,
            actor_id="user-1",
            action="provider.authorize",
            resource="provider:gemini",
            fingerprint="f" * 64,
        )


from creator_app.agnes.execution.approval import StickyApprovalResolver


def test_signed_token_becomes_authenticated_execution_grant():
    a = authority()
    c = challenge(a)
    approval = a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")
    resolver = StickyApprovalResolver()
    grant = a.redeem_to_resolver(
        approval.token,
        resolver=resolver,
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
        authn_method="webauthn",
    )
    assert grant.authenticated is True
    assert grant.actor_id == "user-1"
    assert grant.authn_method == "webauthn"
    assert resolver.is_approved(
        approval_id=grant.approval_id,
        fingerprint="f" * 64,
        require_authenticated=True,
    )


def test_legacy_string_grant_cannot_satisfy_authenticated_gate():
    resolver = StickyApprovalResolver()
    legacy = resolver.grant(
        approval_id="legacy-1",
        fingerprint="f" * 64,
        approved_by="human_governor",
    )
    assert legacy.authenticated is False
    assert resolver.is_approved(
        approval_id=legacy.approval_id,
        fingerprint="f" * 64,
    )
    assert not resolver.is_approved(
        approval_id=legacy.approval_id,
        fingerprint="f" * 64,
        require_authenticated=True,
    )
