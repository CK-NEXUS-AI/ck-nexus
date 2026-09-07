from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.didit_kyb import DIDIT_STATUSES, canonicalize_webhook


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "cknexus-test.db",
        mock_ai=True,
        access_token="",
        rate_limit_per_minute=100,
    )


def _headers() -> dict[str, str]:
    return {
        "X-CK-Gateway-Verified": "1",
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


def _event(status: str, *, event_id: str = "evt-1") -> dict:
    return {
        "event_id": event_id,
        "webhook_type": "business.status.updated",
        "session_id": "sid-1",
        "status": status,
        "vendor_data": "tenant-a:business-42",
        "decision": {"registry_checks": [], "score": 1.0},
    }
def test_native_session_requires_trusted_gateway_identity(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_API_KEY", "server-secret")
    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.post("/api/v1/verification/didit/kyb/session")
    assert response.status_code == 401


def test_native_session_returns_only_native_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DIDIT_API_KEY", "server-secret")
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
