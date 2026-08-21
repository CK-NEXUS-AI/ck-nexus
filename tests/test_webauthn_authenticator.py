from __future__ import annotations

import json

from creator_app.webauthn_authenticator import (
    InMemoryPasskeyStore,
    PasskeyCredential,
    WebAuthnAuthenticatorVerifier,
)


class FakeBackend:
    def __init__(self, *, new_count: int = 2, fail: bool = False) -> None:
        self.new_count = new_count
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def verify_authentication(self, **kwargs) -> int:
        self.calls.append(kwargs)
        if self.fail:
            raise ValueError("invalid assertion")
        return self.new_count


def credential(*, actor_id: str = "user-1", revoked: bool = False):
    return PasskeyCredential(
        credential_id="credential-1",
        actor_id=actor_id,
        public_key_b64="public-key",
        sign_count=1,
        rp_id="example.com",
        origin="https://example.com",
        revoked=revoked,
    )


def assertion() -> str:
    return json.dumps({"id": "credential-1", "type": "public-key"})


def test_actor_bound_assertion_updates_sign_count() -> None:
    store = InMemoryPasskeyStore()
    store.put(credential())
    backend = FakeBackend(new_count=2)
    verifier = WebAuthnAuthenticatorVerifier(store=store, backend=backend)
    assert verifier.verify(
        challenge="challenge-b64",
        assertion=assertion(),
        actor_id="user-1",
    ) is True
    updated = store.get(credential_id="credential-1", actor_id="user-1")
    assert updated is not None and updated.sign_count == 2
    assert backend.calls[0]["rp_id"] == "example.com"
    assert backend.calls[0]["origin"] == "https://example.com"


def test_wrong_actor_is_rejected_before_backend() -> None:
    store = InMemoryPasskeyStore()
    store.put(credential())
    backend = FakeBackend()
    verifier = WebAuthnAuthenticatorVerifier(store=store, backend=backend)
    assert verifier.verify(
        challenge="challenge-b64",
        assertion=assertion(),
        actor_id="other-user",
    ) is False
    assert backend.calls == []


def test_revoked_passkey_is_rejected() -> None:
    store = InMemoryPasskeyStore()
    store.put(credential(revoked=True))
    backend = FakeBackend()
    verifier = WebAuthnAuthenticatorVerifier(store=store, backend=backend)
    assert verifier.verify(
        challenge="challenge-b64",
        assertion=assertion(),
        actor_id="user-1",
    ) is False
    assert backend.calls == []


def test_backend_failure_is_fail_closed() -> None:
    store = InMemoryPasskeyStore()
    store.put(credential())
    verifier = WebAuthnAuthenticatorVerifier(
        store=store,
        backend=FakeBackend(fail=True),
    )
    assert verifier.verify(
        challenge="challenge-b64",
        assertion=assertion(),
        actor_id="user-1",
    ) is False


def test_nonincrementing_counter_is_rejected() -> None:
    store = InMemoryPasskeyStore()
    store.put(credential())
    verifier = WebAuthnAuthenticatorVerifier(
        store=store,
        backend=FakeBackend(new_count=1),
    )
    assert verifier.verify(
        challenge="challenge-b64",
        assertion=assertion(),
        actor_id="user-1",
    ) is False
