from __future__ import annotations

from creator_app.cloud_state import PostgresApprovalReplayStore, PostgresPasskeyStore


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.row = None

    def execute(self, query: str, params: tuple[object, ...] = ()):
        self.calls.append((query, params))

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

def test_postgres_replay_store_inserts_and_checks() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    store = PostgresApprovalReplayStore(lambda: connection)
    store.redeem_once(
        nonce="n1",
        approval_id="a1",
        actor_id="u1",
        subject_digest="d1",
        expires_at=1234.0,
    )
    assert connection.commits == 1
    assert "approval_replay" in cursor.calls[0][0]
    cursor.row = (1,)
    assert store.is_redeemed("n1") is True


def test_postgres_passkey_store_reads_and_updates() -> None:
    cursor = FakeCursor()
    cursor.row = ("cred", "actor", "pk", 2, "rp.example", "https://rp.example", None)
    connection = FakeConnection(cursor)
    store = PostgresPasskeyStore(lambda: connection)
    credential = store.get(credential_id="cred", actor_id="actor")
    assert credential is not None
    assert credential.sign_count == 2
    assert credential.revoked is False
    store.update_sign_count(credential_id="cred", actor_id="actor", sign_count=3)
    assert connection.commits == 1
    assert "passkey_credentials" in cursor.calls[-1][0]
