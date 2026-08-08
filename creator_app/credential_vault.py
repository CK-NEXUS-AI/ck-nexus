from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from creator_app.credential_broker import CredentialId


class CredentialVaultError(RuntimeError):
    """Safe vault error that never contains secret material."""


@dataclass(frozen=True, slots=True)
class VaultAuditEvent:
    credential_id: str
    action: str
    source: str
    version: int
    occurred_at: float

    def as_dict(self) -> dict[str, object]:
        return {
            "credential_id": self.credential_id,
            "action": self.action,
            "source": self.source,
            "version": self.version,
            "occurred_at": self.occurred_at,
        }


class EncryptedCredentialVault:
    """SQLite-backed encrypted credential vault using Fernet authenticated encryption.

    The database never stores the encryption key. Callers must inject the key from the
    runtime environment or an external secret manager.
    """

    def __init__(
        self,
        path: Path,
        key: str | bytes,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        try:
            from cryptography.fernet import Fernet

            self._fernet = Fernet(key.encode("ascii") if isinstance(key, str) else key)
        except (ImportError, ValueError, TypeError) as exc:
            raise CredentialVaultError(
                "Credential vault encryption is unavailable or invalid."
            ) from exc
        self.path = path.expanduser().resolve()
        self._clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS credential_vault (
                    credential_id TEXT PRIMARY KEY,
                    ciphertext BLOB NOT NULL,
                    source TEXT NOT NULL,
                    expires_at REAL,
                    version INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS credential_vault_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credential_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    occurred_at REAL NOT NULL
                );
                """
            )
        try:
            os.chmod(self.path, 0o600)
        except OSError as exc:
            raise CredentialVaultError(
                "Credential vault file permissions could not be secured."
            ) from exc

    def get(self, credential_id: CredentialId) -> tuple[str, str, float | None] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT ciphertext, source, expires_at, version FROM credential_vault "
                "WHERE credential_id = ?",
                (credential_id.value,),
            ).fetchone()
            if row is None:
                return None
            now = self._clock()
            expires_at = row["expires_at"]
            if expires_at is not None and now >= float(expires_at):
                connection.execute(
                    "DELETE FROM credential_vault WHERE credential_id = ?",
                    (credential_id.value,),
                )
                self._audit(
                    connection,
                    credential_id=credential_id,
                    action="expired",
                    source=str(row["source"]),
                    version=int(row["version"]),
                    occurred_at=now,
                )
                return None
            try:
                plaintext = self._fernet.decrypt(bytes(row["ciphertext"])).decode("utf-8")
            except Exception as exc:
                raise CredentialVaultError("Credential vault decryption failed safely.") from exc
            ttl_remaining = (
                max(0.0, float(expires_at) - now) if expires_at is not None else None
            )
            return plaintext, "encrypted-vault", ttl_remaining

    def put(
        self,
        credential_id: CredentialId,
        value: str,
        *,
        source: str,
        ttl_seconds: float | None = None,
    ) -> None:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Persistent credential value cannot be empty.")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive when provided.")
        now = self._clock()
        expires_at = now + ttl_seconds if ttl_seconds is not None else None
        ciphertext = self._fernet.encrypt(candidate.encode("utf-8"))
        with self._connect() as connection:
            row = connection.execute(
                "SELECT version FROM credential_vault WHERE credential_id = ?",
                (credential_id.value,),
            ).fetchone()
            version = int(row["version"]) + 1 if row is not None else 1
            action = "rotated" if row is not None else "created"
            connection.execute(
                """
                INSERT INTO credential_vault
                    (credential_id, ciphertext, source, expires_at, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(credential_id) DO UPDATE SET
                    ciphertext=excluded.ciphertext,
                    source=excluded.source,
                    expires_at=excluded.expires_at,
                    version=excluded.version,
                    updated_at=excluded.updated_at
                """,
                (credential_id.value, ciphertext, source, expires_at, version, now),
            )
            self._audit(
                connection,
                credential_id=credential_id,
                action=action,
                source=source,
                version=version,
                occurred_at=now,
            )

    def delete(self, credential_id: CredentialId, *, reason: str) -> None:
        now = self._clock()
        safe_reason = reason.strip() or "revoked"
        with self._connect() as connection:
            row = connection.execute(
                "SELECT source, version FROM credential_vault WHERE credential_id = ?",
                (credential_id.value,),
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "DELETE FROM credential_vault WHERE credential_id = ?",
                (credential_id.value,),
            )
            self._audit(
                connection,
                credential_id=credential_id,
                action=safe_reason,
                source=str(row["source"]),
                version=int(row["version"]),
                occurred_at=now,
            )

    def rotate_encryption_key(self, new_key: str | bytes) -> None:
        try:
            from cryptography.fernet import Fernet

            replacement = Fernet(
                new_key.encode("ascii") if isinstance(new_key, str) else new_key
            )
        except (ImportError, ValueError, TypeError) as exc:
            raise CredentialVaultError("Replacement vault key is invalid.") from exc
        now = self._clock()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT credential_id, ciphertext, source, version FROM credential_vault"
            ).fetchall()
            prepared: list[tuple[bytes, str, str, int]] = []
            for row in rows:
                try:
                    plaintext = self._fernet.decrypt(bytes(row["ciphertext"]))
                except Exception as exc:
                    raise CredentialVaultError(
                        "Vault key rotation could not decrypt all records."
                    ) from exc
                prepared.append(
                    (
                        replacement.encrypt(plaintext),
                        str(row["credential_id"]),
                        str(row["source"]),
                        int(row["version"]),
                    )
                )
            for ciphertext, credential_id, source, version in prepared:
                connection.execute(
                    "UPDATE credential_vault SET ciphertext = ?, updated_at = ? "
                    "WHERE credential_id = ?",
                    (ciphertext, now, credential_id),
                )
                self._audit_raw(
                    connection,
                    credential_id=credential_id,
                    action="rewrapped",
                    source=source,
                    version=version,
                    occurred_at=now,
                )
        self._fernet = replacement

    def audit_events(self, *, limit: int = 100) -> tuple[VaultAuditEvent, ...]:
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT credential_id, action, source, version, occurred_at "
                "FROM credential_vault_audit ORDER BY id DESC LIMIT ?",
                (bounded,),
            ).fetchall()
        return tuple(
            VaultAuditEvent(
                credential_id=str(row["credential_id"]),
                action=str(row["action"]),
                source=str(row["source"]),
                version=int(row["version"]),
                occurred_at=float(row["occurred_at"]),
            )
            for row in rows
        )

    def _audit(
        self,
        connection: sqlite3.Connection,
        *,
        credential_id: CredentialId,
        action: str,
        source: str,
        version: int,
        occurred_at: float,
    ) -> None:
        self._audit_raw(
            connection,
            credential_id=credential_id.value,
            action=action,
            source=source,
            version=version,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _audit_raw(
        connection: sqlite3.Connection,
        *,
        credential_id: str,
        action: str,
        source: str,
        version: int,
        occurred_at: float,
    ) -> None:
        connection.execute(
            "INSERT INTO credential_vault_audit "
            "(credential_id, action, source, version, occurred_at) VALUES (?, ?, ?, ?, ?)",
            (credential_id, action, source, version, occurred_at),
        )


def build_credential_vault(*, enabled: bool, path: Path) -> EncryptedCredentialVault | None:
    if not enabled:
        return None
    key = os.getenv("CKNEXUS_VAULT_KEY", "").strip()
    if not key:
        raise CredentialVaultError("Credential vault is enabled but CKNEXUS_VAULT_KEY is missing.")
    return EncryptedCredentialVault(path, key)
