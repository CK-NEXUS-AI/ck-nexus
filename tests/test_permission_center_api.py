from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "cknexus.db",
        "mock_ai": True,
        "access_token": "test-token-for-permission-center",
        "rate_limit_per_minute": 50,
    }
    values.update(overrides)
    return Settings(**values)


def test_permission_center_requires_configured_access_token(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, access_token="")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/permissions/grants")
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "PERMISSION_AUTH_NOT_CONFIGURED"


def test_batch_grant_create_evaluate_list_and_revoke(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        assert client.get("/api/permissions/grants").status_code == 401
        headers = {"Authorization": "Bearer test-token-for-permission-center"}
        created = client.post(
            "/api/permissions/grants",
            headers=headers,
            json={
                "grant_id": "batch-test-1",
                "permissions": ["repo.read", "tests.run"],
                "targets": ["repo:CK-NEXUS-AI/ck-nexus"],
                "approved_by": "test-operator",
                "ttl_seconds": 3600,
                "max_cost_usd": 0,
                "high_impact_permissions": [],
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["grant"]["permissions"] == ["repo.read", "tests.run"]

        allowed = client.post(
            "/api/permissions/evaluate",
            headers=headers,
            json={"permission": "tests.run", "target": "repo:CK-NEXUS-AI/ck-nexus"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["allowed"] is True

        denied = client.post(
            "/api/permissions/evaluate",
            headers=headers,
            json={"permission": "repo.delete", "target": "repo:CK-NEXUS-AI/ck-nexus"},
        )
        assert denied.status_code == 200
        assert denied.json()["allowed"] is False

        listed = client.get("/api/permissions/grants", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()["grants"]) == 1

        revoked = client.post(
            "/api/permissions/grants/batch-test-1/revoke",
            headers=headers,
            json={"revoked_by": "test-operator"},
        )
        assert revoked.status_code == 200
        after_revoke = client.post(
            "/api/permissions/evaluate",
            headers=headers,
            json={"permission": "tests.run", "target": "repo:CK-NEXUS-AI/ck-nexus"},
        )
        assert after_revoke.status_code == 200
        assert after_revoke.json()["allowed"] is False


def test_permission_center_page_is_available(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.get("/permissions")
    assert response.status_code == 200
    assert "อนุมัติหลายสิทธิ์" in response.text
    assert "access-token" in response.text
