from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "app.db",
        "mock_ai": True,
        "access_token": "",
        "connector_fabric_enabled": True,
        "connector_allow_private_network": False,
        "connector_registry_path": tmp_path / "connector-registry.json",
        "connector_evidence_path": tmp_path / "connector-evidence.jsonl",
    }
    values.update(overrides)
    return Settings(**values)


def test_connector_api_disabled_is_explicit(tmp_path: Path):
    disabled = settings(tmp_path, connector_fabric_enabled=False)
    with TestClient(create_app(disabled)) as client:
        response = client.get("/api/connectors")
        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "CONNECTOR_FABRIC_DISABLED"


def test_connector_registration_without_discovery_is_persisted(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path, connector_allow_private_network=True))) as client:
        response = client.post(
            "/api/connectors",
            json={
                "connector_id": "local-test",
                "url": "http://127.0.0.1:65535/mcp",
                "protocol": "mcp",
                "allow_private_network": True,
                "auto_discover": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["connector"]["state"] == "REGISTERED"
        assert body["modelTools"] == []

        listed = client.get("/api/connectors")
        assert listed.status_code == 200
        assert listed.json()["connectors"][0]["connectorId"] == "local-test"

        registry_text = (tmp_path / "connector-registry.json").read_text()
        assert "credential" not in registry_text.lower() or "credentialRef" in registry_text


def test_connector_caller_cannot_enable_private_network(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/connectors",
            json={
                "connector_id": "blocked-local",
                "url": "http://127.0.0.1:65535/mcp",
                "protocol": "mcp",
                "allow_private_network": True,
                "auto_discover": False,
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "CONNECTOR_ENDPOINT_REJECTED"


def test_connector_registration_rejects_query_string_secret(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/connectors",
            json={
                "connector_id": "bad",
                "url": "https://example.com/mcp?token=should-not-be-here",
                "protocol": "mcp",
                "auto_discover": False,
            },
        )
        assert response.status_code == 400
        assert "should-not-be-here" not in response.text
