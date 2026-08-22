from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from creator_app.webauthn_authenticator import PasskeyCredential


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
    def __init__(self, factory: PostgresConnectionFactory, *, schema: str = "ck_nexus_dev") -> None:
        self._factory = factory
        self._table = f"{schema}.approval_replay"

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
                    f"INSERT INTO {self._table} "
                    "(nonce, approval_id, actor_id, subject_digest, expires_at) "
                    "VALUES (%s,%s,%s,%s,to_timestamp(%s))",
                    (nonce, approval_id, actor_id, subject_digest, expires_at),
                )
            except Exception as exc:
                raise PermissionError("approval token already redeemed or persistence failed") from exc
            connection.commit()

    def is_redeemed(self, nonce: str) -> bool:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT 1 FROM {self._table} WHERE nonce=%s", (nonce,))
            return cursor.fetchone() is not None


class PostgresPasskeyStore:
    def __init__(self, factory: PostgresConnectionFactory, *, schema: str = "ck_nexus_dev") -> None:
        self._factory = factory
        self._table = f"{schema}.passkey_credentials"

    def get(self, *, credential_id: str, actor_id: str) -> PasskeyCredential | None:
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT credential_id,actor_id,public_key_b64,sign_count,rp_id,origin,revoked_at "
                f"FROM {self._table} WHERE credential_id=%s AND actor_id=%s",
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

    def update_sign_count(self, *, credential_id: str, actor_id: str, sign_count: int) -> None:
        if sign_count < 0:
            raise ValueError("sign_count cannot be negative")
        with self._factory() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE {self._table} SET sign_count=%s,last_used_at=%s "
                "WHERE credential_id=%s AND actor_id=%s",
                (sign_count, datetime.now(UTC), credential_id, actor_id),
            )
            connection.commit()
