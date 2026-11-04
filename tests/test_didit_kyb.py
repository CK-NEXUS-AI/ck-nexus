from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.didit_kyb import (
    DIDIT_KYB_WORKFLOW_ID,
    DIDIT_STATUSES,
    canonicalize_webhook,
)
from creator_app.didit_store import (
    PostgresDiditVerificationStore,
    create_didit_verification_store,
)
from gateway.service_auth import GatewayServiceAuth

SERVICE_AUTH_SECRET = "test-gateway-service-secret-32-bytes-plus"


def _settings(tmp_path: Path, *, access_token: str = "") -> Settings:
    return Settings(
        database_path=tmp_path / "cknexus-test.db",
        mock_ai=True,
        access_token=access_token,
        rate_limit_per_minute=100,
    )


def _headers() -> dict[str, str]:
    token = GatewayServiceAuth(SERVICE_AUTH_SECRET).issue(
        tenant_id="tenant-a",
        actor_id="business-42",
        method="POST",
        path="/api/v1/verification/didit/kyb/session",
    )
    return {
        "X-CK-Gateway-Service-Token": token,
        "X-CK-Tenant-ID": "tenant-a",
        "X-CK-Actor-ID": "business-42",
    }
class _FakeDiditClient:
    def __init__(self) -> None:
        self.vendor_data: str | None = None

    async def create_kyb_session(self, *, vendor_data: str) -> dict[str, str]:
        self.vendor_data = vendor_data
        return {"session_id": "sid-1", "session_token": "native-token"}


def _signed_headers(payload: dict, secret: str) -> dict[str, str]:
    timestamp = int(time.time())
    signature = hmac.new(
        secret.encode("utf-8"),
        canonicalize_webhook(payload),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Timestamp": str(timestamp),
        "X-Signature-V2": signature,
        "Content-Type": "application/json",
    }


class _FakeSharedPostgres:
    def __init__(self) -> None:
        self.events: dict[str, dict] = {}
        self.businesses: dict[str, dict] = {}


class _FakePgCursor:
    def __init__(self, state: _FakeSharedPostgres) -> None:
        self.state = state
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql: str, params=()):
        normalized = " ".join(sql.split())
        if normalized.startswith("INSERT INTO didit_webhook_events"):
            event_id, session_id, vendor_data, status, received_at = params
            if event_id in self.state.events:
                self._row = None
            else:
                self.state.events[event_id] = {
                    "event_id": event_id,
                    "session_id": session_id,
                    "vendor_data": vendor_data,
                    "status": status,
                    "received_at": received_at,
                }
                self._row = {"event_id": event_id}
        elif normalized.startswith("SELECT session_id, status"):
            self._row = self.state.businesses.get(params[0])
        elif normalized.startswith("INSERT INTO didit_business_verifications"):
            vendor_data, session_id, status, verified, decision, resubmit, updated_at = params
            self.state.businesses[vendor_data] = {
                "vendor_data": vendor_data,
                "session_id": session_id,
                "status": status,
                "verified": verified,
                "decision_json": decision,
                "resubmit_json": resubmit,
                "updated_at": updated_at,
            }
        elif normalized.startswith("SELECT * FROM didit_business_verifications"):
            self._row = self.state.businesses.get(params[0])
        else:
            raise AssertionError(f"unexpected SQL in fake Postgres: {normalized}")

    def fetchone(self):
        return self._row


class _FakePgConnection:
    def __init__(self, state: _FakeSharedPostgres) -> None:
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _FakePgCursor(self.state)

    def commit(self):
        return None


class _TestPostgresStore(PostgresDiditVerificationStore):
    def __init__(self, state: _FakeSharedPostgres) -> None:
        super().__init__("postgresql://shared/test")
        self.state = state

    def _connect(self):
        return _FakePgConnection(self.state)


def _event(status: str, *, event_id: str = "evt-1") -> dict:
    return {
        "event_id": event_id,
        "webhook_type": "business.status.updated",
        "workflow_id": DIDIT_KYB_WORKFLOW_ID,
        "session_kind": "business",
        "session_id": "sid-1",
        "status": status,
        "vendor_data": "tenant-a:business-42",
        "decision": {"registry_checks": [], "score": 1.0},
    }
def test_native_session_requires_trusted_gateway_identity(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_API_KEY", "server-secret")
    monkeypatch.setenv("CKNEXUS_GATEWAY_SERVICE_AUTH_SECRET", SERVICE_AUTH_SECRET)
    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.post("/api/v1/verification/didit/kyb/session")
    assert response.status_code == 401


def test_native_session_rejects_forged_gateway_headers_even_with_creator_token(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("DIDIT_API_KEY", "server-secret")
    monkeypatch.setenv("CKNEXUS_GATEWAY_SERVICE_AUTH_SECRET", SERVICE_AUTH_SECRET)
    app = create_app(_settings(tmp_path, access_token="valid-creator-token"))
    app.state.didit_client = _FakeDiditClient()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/verification/didit/kyb/session",
            headers={
                "Authorization": "Bearer valid-creator-token",
                "X-CK-Gateway-Verified": "1",
                "X-CK-Tenant-ID": "forged-tenant",
                "X-CK-Actor-ID": "forged-actor",
            },
        )
    assert response.status_code == 401


def test_native_session_returns_only_native_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_API_KEY", "server-secret")
    monkeypatch.setenv("CKNEXUS_GATEWAY_SERVICE_AUTH_SECRET", SERVICE_AUTH_SECRET)
    app = create_app(_settings(tmp_path))
    fake = _FakeDiditClient()
    app.state.didit_client = fake
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/verification/didit/kyb/session",
            headers=_headers(),
        )
    assert response.status_code == 200
    assert response.json() == {"session_id": "sid-1", "session_token": "native-token"}
    assert fake.vendor_data == "tenant-a:business-42"
    assert "server-secret" not in response.text


def test_webhook_rejects_stale_timestamp(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    payload = _event("Approved")
    headers = _signed_headers(payload, "webhook-secret")
    headers["X-Timestamp"] = str(int(time.time()) - 301)
    with TestClient(app) as client:
        response = client.post("/api/webhooks/didit", json=payload, headers=headers)
    assert response.status_code == 401
def test_webhook_rejects_bad_signature(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    payload = _event("Approved")
    headers = _signed_headers(payload, "wrong-secret")
    with TestClient(app) as client:
        response = client.post("/api/webhooks/didit", json=payload, headers=headers)
    assert response.status_code == 401


def test_webhook_is_idempotent_and_approved_is_authoritative(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    payload = _event("Approved")
    headers = _signed_headers(payload, "webhook-secret")
    with TestClient(app) as client:
        first = client.post("/api/webhooks/didit", json=payload, headers=headers)
        second = client.post("/api/webhooks/didit", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    state = app.state.didit_store.get_business("tenant-a:business-42")
    assert state is not None
    assert state["status"] == "Approved"
    assert state["verified"] == 1


def test_declined_cannot_transition_directly_to_approved(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    declined = _event("Declined", event_id="evt-declined")
    approved = _event("Approved", event_id="evt-approved")
    with TestClient(app) as client:
        first = client.post(
            "/api/webhooks/didit",
            json=declined,
            headers=_signed_headers(declined, "webhook-secret"),
        )
        second = client.post(
            "/api/webhooks/didit",
            json=approved,
            headers=_signed_headers(approved, "webhook-secret"),
        )
    assert first.status_code == 200
    assert second.status_code == 400
    state = app.state.didit_store.get_business("tenant-a:business-42")
    assert state is not None
    assert state["status"] == "Declined"
    assert state["verified"] == 0


@pytest.mark.parametrize("didit_status", sorted(DIDIT_STATUSES))
def test_webhook_covers_every_documented_status(
    tmp_path: Path, monkeypatch, didit_status: str
):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    payload = _event(didit_status, event_id=f"evt-{didit_status}")
    if didit_status == "Resubmitted":
        payload.pop("decision", None)
        payload["resubmit_info"] = {
            "nodes_to_resubmit": ["registry-node"],
            "reasons": {"registry-node": "retry"},
        }
    headers = _signed_headers(payload, "webhook-secret")
    with TestClient(app) as client:
        response = client.post("/api/webhooks/didit", json=payload, headers=headers)
    assert response.status_code == 200
    state = app.state.didit_store.get_business("tenant-a:business-42")
    assert state is not None
    assert state["status"] == didit_status
    assert state["verified"] == (1 if didit_status == "Approved" else 0)


def test_canonicalization_shortens_whole_number_floats():
    assert canonicalize_webhook({"z": 1.0, "a": "ไทย"}) == (
        '{"a":"ไทย","z":1}'.encode()
    )


def test_webhook_rejects_signed_event_from_wrong_workflow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", "webhook-secret")
    app = create_app(_settings(tmp_path))
    payload = _event("Approved", event_id="evt-wrong-workflow")
    payload["workflow_id"] = "00000000-0000-0000-0000-000000000000"
    headers = _signed_headers(payload, "webhook-secret")
    with TestClient(app) as client:
        response = client.post("/api/webhooks/didit", json=payload, headers=headers)
    assert response.status_code == 400
    assert app.state.didit_store.get_business("tenant-a:business-42") is None


def test_postgres_store_dedupes_across_two_replica_instances():
    shared = _FakeSharedPostgres()
    replica_a = _TestPostgresStore(shared)
    replica_b = _TestPostgresStore(shared)
    payload = _event("In Review", event_id="evt-shared")
    first = replica_a.apply_event(payload, received_at=int(time.time()))
    second = replica_b.apply_event(payload, received_at=int(time.time()))
    assert first is True
    assert second is False
    assert len(shared.events) == 1


def test_production_rejects_local_sqlite_didit_store(tmp_path: Path):
    with pytest.raises(RuntimeError, match="shared PostgreSQL"):
        create_didit_verification_store(
            database_path=tmp_path / "local.db",
            database_url="",
            environment="production",
        )


def test_postgres_store_selected_when_shared_database_url_is_configured(tmp_path: Path):
    store = create_didit_verification_store(
        database_path=tmp_path / "ignored.db",
        database_url="postgresql://db.example/cknexus",
        environment="production",
    )
    assert isinstance(store, PostgresDiditVerificationStore)
