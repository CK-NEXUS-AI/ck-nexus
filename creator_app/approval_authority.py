from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from time import time
from typing import Protocol


class AuthenticatorVerifier(Protocol):
    def verify(self, *, challenge: str, assertion: str, actor_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class ApprovalChallenge:
    challenge_id: str
    challenge: str
    actor_id: str
    action: str
    resource: str
    fingerprint: str
    expires_at: float


@dataclass(frozen=True, slots=True)
class VerifiedApproval:
    approval_id: str
    actor_id: str
    action: str
    resource: str
    fingerprint: str
    issued_at: float
    expires_at: float
    token: str


class ApprovalAuthority:
    """Challenge-based approval authority with signed, one-time scoped approvals.

    The authenticator assertion is verified by an injected verifier. This module
    never stores TOTP seeds, passkey private keys, API keys, or raw assertions.
    """

    def __init__(self, *, signing_key: bytes, verifier: AuthenticatorVerifier) -> None:
        if len(signing_key) < 32:
            raise ValueError("approval signing key must be at least 256 bits")
        self._key = signing_key
        self._verifier = verifier
        self._challenges: dict[str, ApprovalChallenge] = {}
        self._redeemed_nonces: set[str] = set()

    def create_challenge(
        self,
        *,
        actor_id: str,
        action: str,
        resource: str,
        fingerprint: str,
        ttl_seconds: int = 120,
    ) -> ApprovalChallenge:
        if not all(v.strip() for v in (actor_id, action, resource, fingerprint)):
            raise ValueError("approval challenge fields cannot be empty")
        if ttl_seconds <= 0 or ttl_seconds > 300:
            raise ValueError("challenge ttl must be between 1 and 300 seconds")
        item = ApprovalChallenge(
            challenge_id=f"apc_{secrets.token_hex(16)}",
            challenge=secrets.token_urlsafe(32),
            actor_id=actor_id.strip(),
            action=action.strip(),
            resource=resource.strip(),
            fingerprint=fingerprint.strip(),
            expires_at=time() + ttl_seconds,
        )
        self._challenges[item.challenge_id] = item
        return item

    def complete_challenge(
        self,
        *,
        challenge_id: str,
        assertion: str,
        ttl_seconds: int = 300,
    ) -> VerifiedApproval:
        item = self._challenges.pop(challenge_id, None)
        if item is None:
            raise PermissionError("approval challenge is unknown or already consumed")
        if item.expires_at <= time():
            raise PermissionError("approval challenge expired")
        if ttl_seconds <= 0 or ttl_seconds > 900:
            raise ValueError("approval ttl must be between 1 and 900 seconds")
        if not self._verifier.verify(
            challenge=item.challenge,
            assertion=assertion,
            actor_id=item.actor_id,
        ):
            raise PermissionError("authenticator assertion failed")

        issued = time()
        nonce = secrets.token_hex(16)
        payload = {
            "approval_id": f"apr_{secrets.token_hex(16)}",
            "actor_id": item.actor_id,
            "action": item.action,
            "resource": item.resource,
            "fingerprint": item.fingerprint,
            "issued_at": issued,
            "expires_at": issued + ttl_seconds,
            "nonce": nonce,
        }
        encoded = self._encode(payload)
        signature = hmac.new(self._key, encoded, hashlib.sha256).digest()
        token = self._b64(encoded) + "." + self._b64(signature)
        return VerifiedApproval(token=token, **{k: payload[k] for k in (
            "approval_id", "actor_id", "action", "resource", "fingerprint", "issued_at", "expires_at"
        )})

    def redeem(
        self,
        token: str,
        *,
        actor_id: str,
        action: str,
        resource: str,
        fingerprint: str,
    ) -> dict[str, object]:
        payload = self._verify_token(token)
        expected = {
            "actor_id": actor_id,
            "action": action,
            "resource": resource,
            "fingerprint": fingerprint,
        }
        for key, value in expected.items():
            if not hmac.compare_digest(str(payload.get(key, "")), value):
                raise PermissionError(f"approval {key} mismatch")
        if float(payload["expires_at"]) <= time():
            raise PermissionError("approval token expired")
        nonce = str(payload["nonce"])
        if nonce in self._redeemed_nonces:
            raise PermissionError("approval token already redeemed")
        self._redeemed_nonces.add(nonce)
        return payload

    def _verify_token(self, token: str) -> dict[str, object]:
        try:
            body_text, sig_text = token.split(".", 1)
            body = self._unb64(body_text)
            signature = self._unb64(sig_text)
        except Exception as exc:
            raise PermissionError("malformed approval token") from exc
        expected = hmac.new(self._key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise PermissionError("approval signature mismatch")
        try:
            return json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise PermissionError("malformed approval payload") from exc

    @staticmethod
    def _encode(payload: dict[str, object]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _unb64(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
