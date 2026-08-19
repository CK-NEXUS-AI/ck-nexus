"""Compatibility facade for the canonical credential broker API.

Post-P0 credential work lives under ``creator_app.credentials`` while existing
CK-NEXUS modules still import ``creator_app.credential_broker``. Re-export the
same class objects so policy/type identity remains stable during migration.
"""

from creator_app.credentials.credential_broker import (
    DEFAULT_CONSUMER_POLICY,
    ENV_BINDINGS,
    CredentialAccessDenied,
    CredentialBroker,
    CredentialId,
    CredentialStatus,
    CredentialUnavailable,
    PersistentCredentialStore,
    SecretLease,
)

__all__ = [
    "DEFAULT_CONSUMER_POLICY",
    "ENV_BINDINGS",
    "CredentialAccessDenied",
    "CredentialBroker",
    "CredentialId",
    "CredentialStatus",
    "CredentialUnavailable",
    "PersistentCredentialStore",
    "SecretLease",
]
