from __future__ import annotations

from creator_app.webauthn_authenticator import (
    PasskeyCredential,
    SQLitePasskeyStore,
)


def credential(*, count: int = 1, revoked: bool = False) -> PasskeyCredential:
    return PasskeyCredential(
        credential_id="cred-1",
        actor_id="user-1",
        public_key_b64="public-key-only",
        sign_count=count,
        rp_id="example.com",
        origin="https://example.com",
        revoked=revoked,
    )


def test_sqlite_store_survives_restart(tmp_path):
    path = tmp_path / "passkeys.db"
    SQLitePasskeyStore(path).put(credential())
    restored = SQLitePasskeyStore(path).get(
        credential_id="cred-1", actor_id="user-1"
    )
    assert restored == credential()


def test_sign_count_update_is_durable(tmp_path):
    path = tmp_path / "passkeys.db"
    store = SQLitePasskeyStore(path)
    store.put(credential())
    store.update_sign_count(
        credential_id="cred-1", actor_id="user-1", sign_count=7
    )
    restored = SQLitePasskeyStore(path).get(
        credential_id="cred-1", actor_id="user-1"
    )
    assert restored is not None
    assert restored.sign_count == 7


def test_revoke_is_durable(tmp_path):
    path = tmp_path / "passkeys.db"
    store = SQLitePasskeyStore(path)
    store.put(credential())
    store.revoke(credential_id="cred-1", actor_id="user-1")
    restored = SQLitePasskeyStore(path).get(
        credential_id="cred-1", actor_id="user-1"
    )
    assert restored is not None
    assert restored.revoked is True
