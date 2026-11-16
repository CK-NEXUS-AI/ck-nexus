from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from deploy.cknexus_chat_ingress import create_app


def test_chat_ingress_forwards_only_scoped_routes_and_auth(monkeypatch):
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "https://ck-nexus-ai.github.io")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"ready": True, "execution_status": "NOT_EXECUTED"},
            headers={"X-Correlation-ID": "test-correlation"},
        )

    app = create_app(transport_factory=lambda: httpx.MockTransport(handler))
    with TestClient(app) as client:
        status = client.get(
            "/api/chat/status",
            headers={
                "Authorization": "Bearer scoped-token",
                "Cookie": "must-not-forward",
                "X-Other": "must-not-forward",
            },
        )
        chat = client.post(
            "/api/chat",
            headers={
                "Authorization": "Bearer scoped-token",
                "Content-Type": "application/json",
            },
            json={"prompt": "test"},
        )
        blocked = client.get("/api/status")

    assert status.status_code == 200
    assert status.json()["ready"] is True
    assert chat.status_code == 200
    assert blocked.status_code == 404
    assert [request.url.path for request in seen] == ["/api/chat/status", "/api/chat"]
    assert all(request.headers["authorization"] == "Bearer scoped-token" for request in seen)
    assert all("cookie" not in request.headers for request in seen)
    assert all("x-other" not in request.headers for request in seen)
    assert seen[1].content == b'{"prompt":"test"}'
    assert status.headers["cache-control"] == "no-store"


def test_chat_ingress_rejects_oversized_body_before_upstream(monkeypatch):
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "https://ck-nexus-ai.github.io")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    app = create_app(transport_factory=lambda: httpx.MockTransport(handler))
    with TestClient(app) as client:
        response = client.post("/api/chat", content=b"x" * 65_537)

    assert response.status_code == 413
    assert calls == 0


def test_chat_ingress_cors_is_exact_origin(monkeypatch):
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "https://ck-nexus-ai.github.io")
    with TestClient(create_app()) as client:
        allowed = client.options(
            "/api/chat",
            headers={
                "Origin": "https://ck-nexus-ai.github.io",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        denied = client.options(
            "/api/chat",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://ck-nexus-ai.github.io"
    assert "access-control-allow-origin" not in denied.headers


def test_chat_ingress_rejects_missing_or_wildcard_origins(monkeypatch):
    monkeypatch.delenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="explicit HTTPS origins"):
        create_app()
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="wildcard is forbidden"):
        create_app()
