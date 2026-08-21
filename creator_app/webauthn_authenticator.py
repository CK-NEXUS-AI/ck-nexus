from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PasskeyCredential:
    credential_id: str
    actor_id: str
    public_key_b64: str
    sign_count: int
    rp_id: str
    origin: str
    revoked: bool = False


class PasskeyCredentialStore(Protocol):
    def get(self, *, credential_id: str, actor_id: str) -> PasskeyCredential | None: ...

    def update_sign_count(
        self, *, credential_id: str, actor_id: str, sign_count: int
    ) -> None: ...


class WebAuthnBackend(Protocol):
    def verify_authentication(
        self,
        *,
        credential_json: str,
        expected_challenge_b64: str,
        rp_id: str,
        origin: str,
        credential_public_key_b64: str,
        current_sign_count: int,
    ) -> int: ...


class PyWebAuthnBackend:
    """Production backend using py_webauthn. Imports lazily for Termux portability."""
    def verify_authentication(
        self,
        *,
        credential_json: str,
        expected_challenge_b64: str,
        rp_id: str,
        origin: str,
        credential_public_key_b64: str,
        current_sign_count: int,
    ) -> int:
        from webauthn import base64url_to_bytes, verify_authentication_response

        verified = verify_authentication_response(
            credential=credential_json,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(credential_public_key_b64),
            credential_current_sign_count=current_sign_count,
            require_user_verification=True,
        )
        return int(verified.new_sign_count)


class InMemoryPasskeyStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], PasskeyCredential] = {}

    def put(self, credential: PasskeyCredential) -> None:
        self._items[(credential.credential_id, credential.actor_id)] = credential

    def get(self, *, credential_id: str, actor_id: str) -> PasskeyCredential | None:
        return self._items.get((credential_id, actor_id))

    def update_sign_count(
        self, *, credential_id: str, actor_id: str, sign_count: int
    ) -> None:
        current = self.get(credential_id=credential_id, actor_id=actor_id)
        if current is None:
            raise KeyError(credential_id)
        self.put(
            PasskeyCredential(
                credential_id=current.credential_id,
                actor_id=current.actor_id,
                public_key_b64=current.public_key_b64,
                sign_count=sign_count,
                rp_id=current.rp_id,
                origin=current.origin,
                revoked=current.revoked,
            )
        )


class WebAuthnAuthenticatorVerifier:
    """Actor-bound WebAuthn verifier for ApprovalAuthority."""

    def __init__(
        self,
        *,
        store: PasskeyCredentialStore,
        backend: WebAuthnBackend | None = None,
    ) -> None:
        self._store = store
        self._backend = backend or PyWebAuthnBackend()

    def verify(self, *, challenge: str, assertion: str, actor_id: str) -> bool:
        try:
            body = json.loads(assertion)
            credential_id = str(body.get("id") or "")
            if not credential_id:
                return False
            credential = self._store.get(
                credential_id=credential_id,
                actor_id=actor_id,
            )
            if credential is None or credential.revoked:
                return False
            new_count = self._backend.verify_authentication(
                credential_json=assertion,
                expected_challenge_b64=challenge,
                rp_id=credential.rp_id,
                origin=credential.origin,
                credential_public_key_b64=credential.public_key_b64,
                current_sign_count=credential.sign_count,
            )
            if credential.sign_count > 0 and new_count <= credential.sign_count:
                return False
            if new_count < 0:
                return False
            self._store.update_sign_count(
                credential_id=credential.credential_id,
                actor_id=actor_id,
                sign_count=new_count,
            )
            return True
        except Exception:
            return False
