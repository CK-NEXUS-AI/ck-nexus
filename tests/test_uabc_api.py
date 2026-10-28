from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def test_uabc_inventory_api_reports_registry_without_claiming_live_connections(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "uabc.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/uabc/platforms")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "PASS"
        assert body["data"]["count"] >= 35
        base44 = next(item for item in body["data"]["platforms"] if item["id"] == "base44")
        assert base44["adapter_implementation"] == "external_chatgpt_connector_only"
        assert "connected" not in base44

        connection = client.post("/api/uabc/platforms/lovable/connection-check")
        assert connection.status_code == 200
        assert connection.json()["status"] == "NOT_TESTED"
        assert connection.json()["data"]["live_test"] == "NOT_TESTED"

        github_capabilities = client.get("/api/uabc/platforms/github/capabilities")
        assert github_capabilities.status_code == 200
        assert github_capabilities.json()["data"]["adapter_registered"] is True
        github_connection = client.post("/api/uabc/platforms/github/connection-check")
        assert github_connection.status_code == 200
        assert github_connection.json()["status"] == "BLOCKED_AUTH"
        assert github_connection.json()["data"]["ui_state"] == "AUTH_REQUIRED"


def test_uabc_operations_fail_closed_and_mutations_need_confirmation(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "uabc-ops.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        missing_confirmation = client.post(
            "/api/uabc/platforms/github/operations",
            json={"operation": "deploy_project"},
        )
        assert missing_confirmation.status_code == 200
        assert missing_confirmation.json()["status"] == "CONFIRMATION_REQUIRED"

        unsupported = client.post(
            "/api/uabc/platforms/lovable/operations",
            json={"operation": "deploy_project", "confirmed": True},
        )
        assert unsupported.status_code == 200
        assert unsupported.json()["status"] == "UNSUPPORTED_OPERATION"


def test_uabc_api_rejects_malformed_operation_payload(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "uabc-bad.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/uabc/platforms/github/operations", json={"confirmed": True})
        assert response.status_code == 400
