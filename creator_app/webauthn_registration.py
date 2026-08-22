from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.parse import urlparse

from creator_app.webauthn_authenticator import PasskeyCredential, PasskeyCredentialStore


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _validate_rp_origin(*, rp_id: str, origin: str) -> None:
    parsed = urlparse(origin)
    hostname = (parsed.hostname or "").lower()
    expected_rp = rp_id.lower().strip()
    if not hostname or not expected_rp:
        raise ValueError("WebAuthn RP ID and origin must be valid")
    if hostname != expected_rp and not hostname.endswith(f".{expected_rp}"):
        raise ValueError("WebAuthn origin is outside the configured RP ID")
    local = hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
        raise ValueError("WebAuthn origin must use HTTPS except for localhost development")


@dataclass(frozen=True, slots=True)
class RegistrationChallenge:
    challenge_id: str
    actor_id: str
    challenge_b64: str
    user_handle_b64: str
    rp_id: str
    origin: str
    expires_at: float


@dataclass(frozen=True, slots=True)
class RegistrationStart:
    challenge_id: str
    options_json: str


class RegistrationChallengeStore(Protocol):
    def put(self, challenge: RegistrationChallenge) -> None: ...

    def consume(
        self, *, challenge_id: str, actor_id: str, now: float
    ) -> RegistrationChallenge | None: ...


class RegistrationBackend(Protocol):
    def generate_options(
        self,
        *,
        rp_id: str,
        rp_name: str,
        user_name: str,
        user_handle_b64: str,
        challenge_b64: str,
    ) -> str: ...

    def verify_registration(
        self,
        *,
        credential_json: str,
        expected_challenge_b64: str,
        rp_id: str,
        origin: str,
    ) -> tuple[str, str, int]: ...


class PyWebAuthnRegistrationBackend:
    """Lazy py_webauthn backend so control-plane imports remain portable."""

    def generate_options(
        self,
        *,
        rp_id: str,
        rp_name: str,
        user_name: str,
        user_handle_b64: str,
        challenge_b64: str,
    ) -> str:
        from webauthn import base64url_to_bytes, generate_registration_options, options_to_json

        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=base64url_to_bytes(user_handle_b64),
            user_name=user_name,
            user_display_name=user_name,
            challenge=base64url_to_bytes(challenge_b64),
        )
        return options_to_json(options)

    def verify_registration(
        self,
        *,
        credential_json: str,
        expected_challenge_b64: str,
        rp_id: str,
        origin: str,
    ) -> tuple[str, str, int]:
        from webauthn import base64url_to_bytes, verify_registration_response

        verified = verify_registration_response(
            credential=credential_json,
            expected_challenge=base64url_to_bytes(expected_challenge_b64),
            expected_origin=origin,
            expected_rp_id=rp_id,
            require_user_verification=True,
        )
        return (
            _b64url(bytes(verified.credential_id)),
            _b64url(bytes(verified.credential_public_key)),
            int(verified.sign_count),
        )


class InMemoryRegistrationChallengeStore:
    def __init__(self) -> None:
        self._items: dict[str, RegistrationChallenge] = {}
        self._consumed: set[str] = set()
        self._lock = Lock()

    def put(self, challenge: RegistrationChallenge) -> None:
        with self._lock:
            if challenge.challenge_id in self._items:
                raise ValueError("registration challenge already exists")
            self._items[challenge.challenge_id] = challenge

    def consume(
        self, *, challenge_id: str, actor_id: str, now: float
    ) -> RegistrationChallenge | None:
        with self._lock:
            challenge = self._items.get(challenge_id)
            if challenge is None or challenge_id in self._consumed:
                return None
            if challenge.actor_id != actor_id or now >= challenge.expires_at:
                return None
            self._consumed.add(challenge_id)
            return challenge


class SQLiteRegistrationChallengeStore:
    """Durable one-time challenge store containing no authenticator secrets."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS webauthn_registration_challenges (
                challenge_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                challenge_b64 TEXT NOT NULL, user_handle_b64 TEXT NOT NULL,
                rp_id TEXT NOT NULL, origin TEXT NOT NULL,
                expires_at REAL NOT NULL, consumed_at REAL)"""
            )
        with contextlib.suppress(OSError):
            os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def put(self, challenge: RegistrationChallenge) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO webauthn_registration_challenges
                (challenge_id,actor_id,challenge_b64,user_handle_b64,rp_id,origin,
                 expires_at,consumed_at) VALUES (?,?,?,?,?,?,?,NULL)""",
                (
                    challenge.challenge_id,
                    challenge.actor_id,
                    challenge.challenge_b64,
                    challenge.user_handle_b64,
                    challenge.rp_id,
                    challenge.origin,
                    challenge.expires_at,
                ),
            )

    def consume(
        self, *, challenge_id: str, actor_id: str, now: float
    ) -> RegistrationChallenge | None:
        with self._connect() as connection:
            result = connection.execute(
                """UPDATE webauthn_registration_challenges SET consumed_at=?
                WHERE challenge_id=? AND actor_id=? AND consumed_at IS NULL
                AND expires_at>?""",
                (now, challenge_id, actor_id, now),
            )
            if result.rowcount != 1:
                return None
            row = connection.execute(
                """SELECT challenge_id,actor_id,challenge_b64,user_handle_b64,
                rp_id,origin,expires_at FROM webauthn_registration_challenges
                WHERE challenge_id=?""",
                (challenge_id,),
            ).fetchone()
        if row is None:
            return None
        return RegistrationChallenge(
            challenge_id=str(row["challenge_id"]),
            actor_id=str(row["actor_id"]),
            challenge_b64=str(row["challenge_b64"]),
            user_handle_b64=str(row["user_handle_b64"]),
            rp_id=str(row["rp_id"]),
            origin=str(row["origin"]),
            expires_at=float(row["expires_at"]),
        )


class PasskeyEnrollmentService:
    def __init__(
        self,
        *,
        rp_id: str,
        rp_name: str,
        origin: str,
        user_handle_key: bytes,
        challenge_store: RegistrationChallengeStore,
        credential_store: PasskeyCredentialStore,
        backend: RegistrationBackend | None = None,
        challenge_ttl_seconds: int = 180,
        clock=time.time,
    ) -> None:
        if not rp_name.strip():
            raise ValueError("WebAuthn RP name cannot be empty")
        _validate_rp_origin(rp_id=rp_id, origin=origin)
        if len(user_handle_key) < 32:
            raise ValueError("user_handle_key must contain at least 32 bytes")
        if not 30 <= challenge_ttl_seconds <= 600:
            raise ValueError("challenge_ttl_seconds must be between 30 and 600")
        self._rp_id = rp_id.strip()
        self._rp_name = rp_name.strip()
        self._origin = origin.strip()
        self._user_handle_key = bytes(user_handle_key)
        self._challenge_store = challenge_store
        self._credential_store = credential_store
        self._backend = backend or PyWebAuthnRegistrationBackend()
        self._challenge_ttl_seconds = challenge_ttl_seconds
        self._clock = clock

    def _user_handle(self, actor_id: str) -> str:
        digest = hmac.new(
            self._user_handle_key,
            actor_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return _b64url(digest)

    def start(self, *, actor_id: str, user_name: str) -> RegistrationStart:
        actor = actor_id.strip()
        username = user_name.strip()
        if not actor or not username:
            raise ValueError("actor_id and user_name cannot be empty")
        challenge = RegistrationChallenge(
            challenge_id=f"wrc_{secrets.token_urlsafe(18)}",
            actor_id=actor,
            challenge_b64=_b64url(secrets.token_bytes(32)),
            user_handle_b64=self._user_handle(actor),
            rp_id=self._rp_id,
            origin=self._origin,
            expires_at=self._clock() + self._challenge_ttl_seconds,
        )
        options = self._backend.generate_options(
            rp_id=self._rp_id,
            rp_name=self._rp_name,
            user_name=username,
            user_handle_b64=challenge.user_handle_b64,
            challenge_b64=challenge.challenge_b64,
        )
        self._challenge_store.put(challenge)
        return RegistrationStart(
            challenge_id=challenge.challenge_id,
            options_json=options,
        )

    def complete(
        self, *, challenge_id: str, actor_id: str, credential_json: str
    ) -> PasskeyCredential:
        challenge = self._challenge_store.consume(
            challenge_id=challenge_id,
            actor_id=actor_id,
            now=self._clock(),
        )
        if challenge is None:
            raise PermissionError("registration challenge invalid, expired, or already consumed")
        if not credential_json.strip():
            raise PermissionError("registration credential is required")
        credential_id, public_key_b64, sign_count = self._backend.verify_registration(
            credential_json=credential_json,
            expected_challenge_b64=challenge.challenge_b64,
            rp_id=challenge.rp_id,
            origin=challenge.origin,
        )
        if not credential_id or not public_key_b64 or sign_count < 0:
            raise PermissionError("registration verification returned invalid credential metadata")
        credential = PasskeyCredential(
            credential_id=credential_id,
            actor_id=challenge.actor_id,
            public_key_b64=public_key_b64,
            sign_count=sign_count,
            rp_id=challenge.rp_id,
            origin=challenge.origin,
        )
        self._credential_store.put(credential)
        return credential
