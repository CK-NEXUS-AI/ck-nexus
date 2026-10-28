from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "creator_app/web/automation.html"


def test_automation_route_serves_dedicated_control_center(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "automation.db", mock_ai=True, access_token="")
    with TestClient(create_app(settings)) as client:
        response = client.get("/automation")
    assert response.status_code == 200
    assert 'id="automation-control-center"' in response.text
    assert "CK-NEXUS Automation Control Center" in response.text


def test_automation_page_uses_real_read_only_status_endpoints_and_no_fake_connected_state():
    source = PAGE.read_text(encoding="utf-8")
    script = (ROOT / "creator_app/web/automation.js").read_text(encoding="utf-8")
    for endpoint in (
        "/api/automation/status",
        "/api/automation/n8n",
        "/api/integrations/gmail/oauth/start",
    ):
        assert endpoint in script
    assert "AbortController" in script
    assert "textContent" in script
    assert "localStorage" not in source + script
    assert "sessionStorage" not in source + script
    assert "ยังไม่ได้ตรวจสอบ" in source


def test_n8n_status_proxy_returns_only_validated_workflow_counts(tmp_path: Path, monkeypatch):
    import json
    import urllib.request

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"ok": True, "count": 3, "workflows": [
                {"id": "a", "name": "Active", "active": True},
                {"id": "b", "name": "Inactive", "active": False},
                "invalid-row",
            ]}).encode()

    seen = {}
    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    settings = Settings(
        database_path=tmp_path / "automation-proxy.db", mock_ai=True, access_token=""
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/automation/n8n")
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["active"] == 1
    assert seen == {"url": "http://127.0.0.1:8791/api/workflows", "timeout": 4}


def test_n8n_status_proxy_requires_access_token_when_configured(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "automation-auth.db",
        mock_ai=True,
        access_token="unit-test-token",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/automation/n8n")
    assert response.status_code == 401
    assert "unit-test-token" not in response.text


def test_automation_status_reports_gateway_evidence_without_claiming_live_ai_or_gmail(
    tmp_path: Path, monkeypatch
):
    import json
    import urllib.request

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.body).encode()

    def fake_urlopen(request, timeout):
        url = request.full_url
        if url.endswith('/v1/scanner/health'):
            return FakeResponse({'reachable': True})
        if url.endswith('/v1/status'):
            return FakeResponse({'upstream_integrations': 'configured'})
        if url.endswith('/health'):
            return FakeResponse({'status': 'ok'})
        raise AssertionError(f'Unexpected local endpoint: {url}')

    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)
    settings = Settings(
        database_path=tmp_path / 'automation-status.db', mock_ai=True, access_token=''
    )
    with TestClient(create_app(settings)) as client:
        response = client.get('/api/automation/status')
    assert response.status_code == 200
    body = response.json()
    assert [item['state'] for item in body['services']] == ['ok', 'ok', 'ok']
    assert body['integrations'][0]['state'] == 'pending'
    assert body['gmail_oauth_available'] is False
    assert 'secret' not in response.text.lower()
