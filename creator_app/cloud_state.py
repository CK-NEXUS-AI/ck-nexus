from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from creator_app.webauthn_authenticator import PasskeyCredential
from creator_app.webauthn_registration import RegistrationChallenge


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[object, ...] = ()) -> object: ...
    def fetchone(self) -> object | None: ...


class ConnectionLike(Protocol):
    def __enter__(self): ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
    def cursor(self) -> CursorLike: ...
    def commit(self) -> None: ...


class PostgresConnectionFactory(Protocol):
    def __call__(self) -> ConnectionLike: ...


class PostgresApprovalReplayStore:
    def __init__(self, factory: PostgresConnectionFactory) -> None:
        self._factory = factory

    def redeem_once(
        self,
        *,
        nonce: str,
        approval_id: str,
        actor_id: str,
        subject_digest: str,
        expires_at: float,
    ) -> None:
        if not all((nonce, approval_id, actor_id, subject_digest)):
            raise ValueError("replay fields cannot be empty")
        with self._factory() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO ck_nexus_dev.approval_replay "
                    "(nonce, approval_id, actor_id, subject_digest, expires_at) "
                    "VALUES (%s,%s,%s,%s,to_timestamp(%s))",
                    (nonce, approval_id, actor_id, subject_digest, expires_at),
                )
            except Exception as exc:
                raise PermissionError(
                    "approval token already redeemed or persistence failed"
                ) from exc
            connection.commit()

    def is_redeemed(self, nonce: str) -> bool:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT 1 FROM ck_nexus_dev.approval_replay WHERE nonce=%s", (nonce,)
            )
            return cursor.fetchone() is not None


class PostgresPasskeyStore:
    def __init__(self, factory: PostgresConnectionFactory) -> None:
        self._factory = factory

    def put(self, credential: PasskeyCredential) -> None:
        if credential.sign_count < 0:
            raise ValueError("sign_count cannot be negative")
        with self._factory() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO ck_nexus_dev.passkey_credentials "
                    "(credential_id,actor_id,public_key_b64,sign_count,rp_id,origin) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        credential.credential_id,
                        credential.actor_id,
                        credential.public_key_b64,
                        credential.sign_count,
                        credential.rp_id,
                        credential.origin,
                    ),
                )
            except Exception as exc:
                raise ValueError("passkey enrollment persistence failed") from exc
            connection.commit()

    def get(self, *, credential_id: str, actor_id: str) -> PasskeyCredential | None:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT credential_id,actor_id,public_key_b64,sign_count,rp_id,origin,revoked_at "
                "FROM ck_nexus_dev.passkey_credentials "
                "WHERE credential_id=%s AND actor_id=%s",
                (credential_id, actor_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return PasskeyCredential(
            credential_id=str(row[0]),
            actor_id=str(row[1]),
            public_key_b64=str(row[2]),
            sign_count=int(row[3]),
            rp_id=str(row[4]),
            origin=str(row[5]),
            revoked=row[6] is not None,
        )

    def update_sign_count(
        self, *, credential_id: str, actor_id: str, sign_count: int
    ) -> None:
        if sign_count < 0:
            raise ValueError("sign_count cannot be negative")
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE ck_nexus_dev.passkey_credentials "
                "SET sign_count=%s,last_used_at=%s "
                "WHERE credential_id=%s AND actor_id=%s AND revoked_at IS NULL RETURNING 1",
                (sign_count, datetime.now(UTC), credential_id, actor_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(credential_id)
            connection.commit()

    def revoke(self, *, credential_id: str, actor_id: str) -> None:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE ck_nexus_dev.passkey_credentials SET revoked_at=%s "
                "WHERE credential_id=%s AND actor_id=%s AND revoked_at IS NULL RETURNING 1",
                (datetime.now(UTC), credential_id, actor_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(credential_id)
            connection.commit()


class PostgresRegistrationChallengeStore:
    def __init__(self, factory: PostgresConnectionFactory) -> None:
        self._factory = factory

    def put(self, challenge: RegistrationChallenge) -> None:
        with self._factory() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO ck_nexus_dev.webauthn_registration_challenges "
                    "(challenge_id,actor_id,challenge_b64,user_handle_b64,rp_id,origin,expires_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,to_timestamp(%s))",
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
            except Exception as exc:
                raise ValueError("registration challenge persistence failed") from exc
            connection.commit()

    def consume(
        self, *, challenge_id: str, actor_id: str, now: float
    ) -> RegistrationChallenge | None:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE ck_nexus_dev.webauthn_registration_challenges "
                "SET consumed_at=to_timestamp(%s) "
                "WHERE challenge_id=%s AND actor_id=%s AND consumed_at IS NULL "
                "AND expires_at>to_timestamp(%s) "
                "RETURNING challenge_id,actor_id,challenge_b64,user_handle_b64," 
                "rp_id,origin,extract(epoch from expires_at)",
                (now, challenge_id, actor_id, now),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            connection.commit()
        return RegistrationChallenge(
            challenge_id=str(row[0]),
            actor_id=str(row[1]),
            challenge_b64=str(row[2]),
            user_handle_b64=str(row[3]),
            rp_id=str(row[4]),
            origin=str(row[5]),
            expires_at=float(row[6]),
        )
