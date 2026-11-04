from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Protocol


class CredentialId(StrEnum):
    OPENAI_API_KEY = "openai.api_key"
    GMAIL_CLIENT_ID = "gmail.client_id"
    GMAIL_CLIENT_SECRET = "gmail.client_secret"
    GMAIL_ACCESS_TOKEN = "gmail.access_token"
    GMAIL_REFRESH_TOKEN = "gmail.refresh_token"
    GITHUB_APP_ID = "github.app_id"
    GITHUB_APP_PRIVATE_KEY = "github.app_private_key"
    GITHUB_APP_INSTALLATION_ID = "github.app_installation_id"
    GITHUB_INSTALLATION_TOKEN = "github.installation_token"
    PINTEREST_ACCESS_TOKEN = "pinterest.access_token"


ENV_BINDINGS: Mapping[CredentialId, str] = {
    CredentialId.OPENAI_API_KEY: "OPENAI_API_KEY",
    CredentialId.GMAIL_CLIENT_ID: "GMAIL_CLIENT_ID",
    CredentialId.GMAIL_CLIENT_SECRET: "GMAIL_CLIENT_SECRET",
    CredentialId.GMAIL_ACCESS_TOKEN: "GMAIL_ACCESS_TOKEN",
    CredentialId.GMAIL_REFRESH_TOKEN: "GMAIL_REFRESH_TOKEN",
    CredentialId.GITHUB_APP_ID: "GITHUB_APP_ID",
    CredentialId.GITHUB_APP_PRIVATE_KEY: "GITHUB_APP_PRIVATE_KEY",
    CredentialId.GITHUB_APP_INSTALLATION_ID: "GITHUB_APP_INSTALLATION_ID",
    CredentialId.GITHUB_INSTALLATION_TOKEN: "GITHUB_APP_INSTALLATION_TOKEN",
    CredentialId.PINTEREST_ACCESS_TOKEN: "PINTEREST_ACCESS_TOKEN",
}


DEFAULT_CONSUMER_POLICY: Mapping[str, frozenset[CredentialId]] = {
    "provider.openai": frozenset({CredentialId.OPENAI_API_KEY}),
    "council.openai": frozenset({CredentialId.OPENAI_API_KEY}),
    "gmail.oauth": frozenset(
        {
            CredentialId.GMAIL_CLIENT_ID,
            CredentialId.GMAIL_CLIENT_SECRET,
            CredentialId.GMAIL_ACCESS_TOKEN,
            CredentialId.GMAIL_REFRESH_TOKEN,
        }
    ),
    "gmail.api": frozenset(
        {
            CredentialId.GMAIL_ACCESS_TOKEN,
            CredentialId.GMAIL_REFRESH_TOKEN,
        }
    ),
    "pinterest.api": frozenset({CredentialId.PINTEREST_ACCESS_TOKEN}),
    "github.app": frozenset(
        {
            CredentialId.GITHUB_APP_ID,
            CredentialId.GITHUB_APP_PRIVATE_KEY,
            CredentialId.GITHUB_APP_INSTALLATION_ID,
            CredentialId.GITHUB_INSTALLATION_TOKEN,
        }
    ),
}


class CredentialAccessDenied(PermissionError):
    """Raised when a consumer asks for a secret outside its explicit policy."""


class CredentialUnavailable(RuntimeError):
    """Raised when an allowed credential is not configured or has expired."""


class PersistentCredentialStore(Protocol):
    """Minimal encrypted-store boundary used by the broker."""

    def get(self, credential_id: CredentialId) -> tuple[str, str, float | None] | None: ...

    def put(
        self,
        credential_id: CredentialId,
        value: str,
        *,
        source: str,
        ttl_seconds: float | None = None,
    ) -> None: ...

    def delete(self, credential_id: CredentialId, *, reason: str) -> None: ...


@dataclass(frozen=True, slots=True, repr=False)
class SecretLease:
    credential_id: CredentialId
    consumer: str
    source: str
    _value: str
    expires_at: float | None = None

    def reveal(self, *, consumer: str) -> str:
        if consumer != self.consumer:
            raise CredentialAccessDenied("Credential lease is bound to a different consumer.")
        if self.expires_at is not None and monotonic() >= self.expires_at:
            raise CredentialUnavailable("Credential lease expired.")
        return self._value

    def __repr__(self) -> str:
        state = "expiring" if self.expires_at is not None else "static"
        return (
            f"SecretLease(credential_id={self.credential_id!r}, consumer={self.consumer!r}, "
            f"source={self.source!r}, value=<redacted>, state={state!r})"
        )


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    credential_id: CredentialId
    configured: bool
    source: str | None
    ephemeral: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.credential_id.value,
            "configured": self.configured,
            "source": self.source,
            "ephemeral": self.ephemeral,
        }


@dataclass(slots=True)
class _EphemeralSecret:
    value: str
    expires_at: float | None
    source: str


class CredentialBroker:
    """Least-privilege credential broker with redacted status and consumer-bound leases.

    The broker intentionally does not expose a bulk export API. Callers must request one
    credential for one named consumer and receive a lease bound to that consumer.
    """

    def __init__(
        self,
        *,
        environment: Mapping[CredentialId, str] | None = None,
        policy: Mapping[str, frozenset[CredentialId]] | None = None,
        persistent_store: PersistentCredentialStore | None = None,
    ) -> None:
        self._environment = dict(environment or {})
        self._policy = dict(policy or DEFAULT_CONSUMER_POLICY)
        self._ephemeral: dict[CredentialId, _EphemeralSecret] = {}
        self._persistent_store = persistent_store

    @classmethod
    def from_environment(
        cls,
        *,
        persistent_store: PersistentCredentialStore | None = None,
    ) -> CredentialBroker:
        values: dict[CredentialId, str] = {}
        for credential_id, env_name in ENV_BINDINGS.items():
            value = os.getenv(env_name, "").strip()
            if value:
                values[credential_id] = value
        return cls(environment=values, persistent_store=persistent_store)

    @property
    def persistent_available(self) -> bool:
        return self._persistent_store is not None

    def is_allowed(self, credential_id: CredentialId, *, consumer: str) -> bool:
        return credential_id in self._policy.get(consumer, frozenset())

    def is_configured(self, credential_id: CredentialId, *, consumer: str) -> bool:
        if not self.is_allowed(credential_id, consumer=consumer):
            return False
        return self._resolve(credential_id) is not None

    def acquire(self, credential_id: CredentialId, *, consumer: str) -> SecretLease:
        if not self.is_allowed(credential_id, consumer=consumer):
            raise CredentialAccessDenied("Credential access is not allowed for this consumer.")
        resolved = self._resolve(credential_id)
        if resolved is None:
            raise CredentialUnavailable("Required credential is not configured.")
        value, source, expires_at = resolved
        return SecretLease(
            credential_id=credential_id,
            consumer=consumer,
            source=source,
            _value=value,
            expires_at=expires_at,
        )

    def put_ephemeral(
        self,
        credential_id: CredentialId,
        value: str,
        *,
        source: str,
        ttl_seconds: float | None = None,
    ) -> None:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Ephemeral credential value cannot be empty.")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive when provided.")
        expires_at = monotonic() + ttl_seconds if ttl_seconds is not None else None
        self._ephemeral[credential_id] = _EphemeralSecret(
            value=candidate,
            expires_at=expires_at,
            source=source,
        )

    def clear_ephemeral(self, credential_id: CredentialId) -> None:
        self._ephemeral.pop(credential_id, None)

    def put_persistent(
        self,
        credential_id: CredentialId,
        value: str,
        *,
        source: str,
        ttl_seconds: float | None = None,
    ) -> None:
        if self._persistent_store is None:
            raise CredentialUnavailable("Persistent credential storage is unavailable.")
        self._persistent_store.put(
            credential_id,
            value,
            source=source,
            ttl_seconds=ttl_seconds,
        )

    def clear_persistent(self, credential_id: CredentialId, *, reason: str = "revoked") -> None:
        if self._persistent_store is None:
            return
        self._persistent_store.delete(credential_id, reason=reason)

    def statuses(self, *, consumer: str) -> tuple[CredentialStatus, ...]:
        allowed = sorted(self._policy.get(consumer, frozenset()), key=lambda item: item.value)
        result: list[CredentialStatus] = []
        for credential_id in allowed:
            resolved = self._resolve(credential_id)
            if resolved is None:
                result.append(CredentialStatus(credential_id, False, None, False))
                continue
            _, source, _ = resolved
            result.append(
                CredentialStatus(
                    credential_id=credential_id,
                    configured=True,
                    source=source,
                    ephemeral=credential_id in self._ephemeral,
                )
            )
        return tuple(result)

    def __repr__(self) -> str:
        configured = sum(
            1 for credential_id in CredentialId if self._resolve(credential_id) is not None
        )
        return f"CredentialBroker(configured={configured}, values=<redacted>)"

    def _resolve(self, credential_id: CredentialId) -> tuple[str, str, float | None] | None:
        ephemeral = self._ephemeral.get(credential_id)
        if ephemeral is not None:
            if ephemeral.expires_at is not None and monotonic() >= ephemeral.expires_at:
                self._ephemeral.pop(credential_id, None)
            else:
                return ephemeral.value, ephemeral.source, ephemeral.expires_at
        if self._persistent_store is not None:
            persisted = self._persistent_store.get(credential_id)
            if persisted is not None:
                value, source, ttl_remaining = persisted
                expires_at = monotonic() + ttl_remaining if ttl_remaining is not None else None
                return value, source, expires_at
        value = self._environment.get(credential_id, "").strip()
        if not value:
            return None
        return value, "environment", None
