from __future__ import annotations

import pytest

from creator_app.webauthn_authenticator import InMemoryPasskeyStore
from creator_app.webauthn_registration import (
    InMemoryRegistrationChallengeStore,
    PasskeyEnrollmentService,
    RegistrationChallenge,
    SQLiteRegistrationChallengeStore,
)


class FakeRegistrationBackend:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.generated: list[dict[str, object]] = []
        self.verified: list[dict[str, object]] = []

    def generate_options(self, **kwargs) -> str:
        self.generated.append(kwargs)
        return '{"publicKey":"options"}'

    def verify_registration(self, **kwargs) -> tuple[str, str, int]:
        self.verified.append(kwargs)
        if self.fail:
            raise ValueError("bad attestation")
        return ("cred-1", "public-key-b64", 0)


def make_service(*, now: list[float], backend: FakeRegistrationBackend):
    credentials = InMemoryPasskeyStore()
    challenges = InMemoryRegistrationChallengeStore()
    value = PasskeyEnrollmentService(
        rp_id="example.com",
        rp_name="CK-NEXUS",
        origin="https://login.example.com",
        user_handle_key=b"k" * 32,
        challenge_store=challenges,
        credential_store=credentials,
        backend=backend,
        challenge_ttl_seconds=60,
        clock=lambda: now[0],
    )
    return value, credentials


def test_start_and_complete_enrollment_binds_actor_and_rp() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend()
    value, credentials = make_service(now=now, backend=backend)
    start = value.start(actor_id="user-1", user_name="user@example.com")
    assert start.challenge_id.startswith("wrc_")
    assert backend.generated[0]["rp_id"] == "example.com"
    result = value.complete(
        challenge_id=start.challenge_id,
        actor_id="user-1",
        credential_json='{"id":"cred-1"}',
    )
    assert result.actor_id == "user-1"
    assert result.rp_id == "example.com"
    stored = credentials.get(credential_id="cred-1", actor_id="user-1")
    assert stored == result
    assert backend.verified[0]["origin"] == "https://login.example.com"


def test_user_handle_is_stable_and_actor_scoped() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend()
    value, _ = make_service(now=now, backend=backend)
    value.start(actor_id="user-1", user_name="one")
    value.start(actor_id="user-1", user_name="one-again")
    value.start(actor_id="user-2", user_name="two")
    first = backend.generated[0]["user_handle_b64"]
    second = backend.generated[1]["user_handle_b64"]
    third = backend.generated[2]["user_handle_b64"]
    assert first == second
    assert first != third


def test_registration_challenge_is_one_time() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend()
    value, _ = make_service(now=now, backend=backend)
    start = value.start(actor_id="user-1", user_name="u")
    value.complete(
        challenge_id=start.challenge_id,
        actor_id="user-1",
        credential_json='{"id":"cred-1"}',
    )
    with pytest.raises(PermissionError, match="already consumed"):
        value.complete(
            challenge_id=start.challenge_id,
            actor_id="user-1",
            credential_json='{"id":"cred-1"}',
        )


def test_wrong_actor_does_not_claim_challenge() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend()
    value, _ = make_service(now=now, backend=backend)
    start = value.start(actor_id="user-1", user_name="u")
    with pytest.raises(PermissionError):
        value.complete(
            challenge_id=start.challenge_id,
            actor_id="attacker",
            credential_json='{"id":"cred-1"}',
        )
    result = value.complete(
        challenge_id=start.challenge_id,
        actor_id="user-1",
        credential_json='{"id":"cred-1"}',
    )
    assert result.actor_id == "user-1"


def test_expired_challenge_is_rejected() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend()
    value, _ = make_service(now=now, backend=backend)
    start = value.start(actor_id="user-1", user_name="u")
    now[0] = 1061.0
    with pytest.raises(PermissionError):
        value.complete(
            challenge_id=start.challenge_id,
            actor_id="user-1",
            credential_json='{"id":"cred-1"}',
        )
    assert backend.verified == []


def test_failed_attestation_consumes_challenge() -> None:
    now = [1000.0]
    backend = FakeRegistrationBackend(fail=True)
    value, _ = make_service(now=now, backend=backend)
    start = value.start(actor_id="user-1", user_name="u")
    with pytest.raises(ValueError, match="bad attestation"):
        value.complete(
            challenge_id=start.challenge_id,
            actor_id="user-1",
            credential_json='{"id":"cred-1"}',
        )
    with pytest.raises(PermissionError):
        value.complete(
            challenge_id=start.challenge_id,
            actor_id="user-1",
            credential_json='{"id":"cred-1"}',
        )


def test_sqlite_challenge_survives_restart_and_consumes_once(tmp_path) -> None:
    path = tmp_path / "registration.db"
    challenge = RegistrationChallenge(
        challenge_id="wrc-1",
        actor_id="user-1",
        challenge_b64="challenge",
        user_handle_b64="handle",
        rp_id="example.com",
        origin="https://example.com",
        expires_at=2000.0,
    )
    SQLiteRegistrationChallengeStore(path).put(challenge)
    restored = SQLiteRegistrationChallengeStore(path)
    assert restored.consume(
        challenge_id="wrc-1",
        actor_id="user-1",
        now=1000.0,
    ) == challenge
    assert restored.consume(
        challenge_id="wrc-1",
        actor_id="user-1",
        now=1000.0,
    ) is None


def test_invalid_origin_and_short_user_handle_key_are_rejected() -> None:
    kwargs = {
        "rp_id": "example.com",
        "rp_name": "CK-NEXUS",
        "origin": "http://example.com",
        "user_handle_key": b"k" * 32,
        "challenge_store": InMemoryRegistrationChallengeStore(),
        "credential_store": InMemoryPasskeyStore(),
    }
    with pytest.raises(ValueError, match="HTTPS"):
        PasskeyEnrollmentService(**kwargs)
    kwargs["origin"] = "https://example.com"
    kwargs["user_handle_key"] = b"short"
    with pytest.raises(ValueError, match="32 bytes"):
        PasskeyEnrollmentService(**kwargs)
