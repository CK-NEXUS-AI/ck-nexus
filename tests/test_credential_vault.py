from __future__ import annotations

from pathlib import Path

import pytest
from creator_app.credential_broker import CredentialBroker, CredentialId, CredentialUnavailable
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.credential_vault import CredentialVaultError, EncryptedCredentialVault


def test_vault_persists_encrypted_secret_across_broker_restart(tmp_path: Path) -> None:
    key = Fernet.generate_key()
    path = tmp_path / "credentials.db"
    vault = EncryptedCredentialVault(path, key)
    broker = CredentialBroker(persistent_store=vault)

    broker.put_persistent(
        CredentialId.GMAIL_REFRESH_TOKEN,
        "refresh-secret-value",
        source="gmail-oauth",
    )

    raw = path.read_bytes()
    assert b"refresh-secret-value" not in raw
    restarted = CredentialBroker(persistent_store=EncryptedCredentialVault(path, key))
    lease = restarted.acquire(CredentialId.GMAIL_REFRESH_TOKEN, consumer="gmail.api")
    assert lease.reveal(consumer="gmail.api") == "refresh-secret-value"
    assert "refresh-secret-value" not in repr(restarted)


def test_vault_rotation_and_revocation_are_audited_without_secret(tmp_path: Path) -> None:
    key = Fernet.generate_key()
    vault = EncryptedCredentialVault(tmp_path / "credentials.db", key)
    broker = CredentialBroker(persistent_store=vault)
    credential_id = CredentialId.GMAIL_REFRESH_TOKEN

    broker.put_persistent(credential_id, "first-secret", source="gmail-oauth")
    broker.put_persistent(credential_id, "second-secret", source="gmail-oauth")
    broker.clear_persistent(credential_id, reason="revoked")

    with pytest.raises(CredentialUnavailable):
        broker.acquire(credential_id, consumer="gmail.api")
    events = [event.as_dict() for event in vault.audit_events()]
    serialized = repr(events)
    assert {event["action"] for event in events} >= {"created", "rotated", "revoked"}
    assert "first-secret" not in serialized
    assert "second-secret" not in serialized


def test_vault_master_key_rotation_rewraps_all_records(tmp_path: Path) -> None:
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    path = tmp_path / "credentials.db"
    vault = EncryptedCredentialVault(path, old_key)
    broker = CredentialBroker(persistent_store=vault)
    broker.put_persistent(
        CredentialId.GITHUB_INSTALLATION_TOKEN,
        "short-lived-token",
        source="github-app",
        ttl_seconds=3600,
    )

    vault.rotate_encryption_key(new_key)
    reopened = CredentialBroker(persistent_store=EncryptedCredentialVault(path, new_key))
    lease = reopened.acquire(
        CredentialId.GITHUB_INSTALLATION_TOKEN,
        consumer="github.app",
    )
    assert lease.reveal(consumer="github.app") == "short-lived-token"

    old = EncryptedCredentialVault(path, old_key)
    with pytest.raises(CredentialVaultError, match="decryption failed"):
        old.get(CredentialId.GITHUB_INSTALLATION_TOKEN)


def test_vault_file_permissions_are_owner_only(tmp_path: Path) -> None:
    path = tmp_path / "credentials.db"
    EncryptedCredentialVault(path, Fernet.generate_key())
    assert path.stat().st_mode & 0o777 == 0o600


def test_app_wires_vault_with_redacted_status(tmp_path: Path, monkeypatch) -> None:
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("CKNEXUS_VAULT_KEY", key)
    settings = Settings(
        database_path=tmp_path / "app.db",
        mock_ai=True,
        credential_vault_enabled=True,
        credential_vault_path=tmp_path / "vault.db",
        credential_vault_key_configured=True,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/security/credential-vault/status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["backend"] == "sqlite-fernet"
    assert body["secrets_exposed"] is False
    assert key not in response.text
