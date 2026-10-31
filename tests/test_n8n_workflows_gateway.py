from __future__ import annotations

import http.client
import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

GATEWAY_PATH = Path(__file__).resolve().parents[1] / "ops/vps/services/cknexus_n8n_workflows_ui.py"
spec = importlib.util.spec_from_file_location("cknexus_n8n_workflows_ui", GATEWAY_PATH)
gateway = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gateway)


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()

    def getcode(self):
        return self.status


def get_json(monkeypatch, payloads):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append((request.full_url, timeout))
        payload = payloads.pop(0)
        return FakeResponse(payload)

    monkeypatch.setattr(gateway.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    server = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        conn.request("GET", "/api/workflows")
        response = conn.getresponse()
        body = json.loads(response.read())
        assert response.status == 200
        conn.close()
        return body, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_workflow_list_follows_n8n_next_cursor(monkeypatch):
    body, calls = get_json(
        monkeypatch,
        [
            {"data": [{"id": "w1", "name": "งานหนึ่ง", "active": False}], "nextCursor": "cursor-2"},
            {"data": [{"id": "w2", "name": "งานสอง", "active": True}], "nextCursor": None},
        ],
    )
    assert body["ok"] is True
    assert body["count"] == 2
    assert [row["id"] for row in body["workflows"]] == ["w1", "w2"]
    assert len(calls) == 2
    assert "cursor=cursor-2" in calls[1][0]


def test_workflow_list_empty_is_a_valid_contract(monkeypatch):
    body, calls = get_json(monkeypatch, [{"data": [], "nextCursor": None}])
    assert body == {"ok": True, "count": 0, "workflows": [], "nextCursor": None}
    assert len(calls) == 1


def test_upstream_http_error_is_sanitized(monkeypatch):
    def fail(request, timeout=None):
        raise gateway.urllib.error.HTTPError(request.full_url, 401, "bad", {}, None)

    monkeypatch.setattr(gateway.urllib.request, "urlopen", fail)
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("GET", "workflows?limit=1")
    assert err.value.status == 401
    assert "secret" not in err.value.safe_message.lower()
    assert "test-secret-sentinel" not in str(err.value)
    assert "bad" not in str(err.value)


def test_timeout_is_mapped_to_safe_gateway_error(monkeypatch):
    def fail(request, timeout=None):
        raise TimeoutError("test-secret-sentinel upstream detail")

    monkeypatch.setattr(gateway.urllib.request, "urlopen", fail)
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("GET", "workflows?limit=1")
    assert err.value.status == 504
    assert "test-secret-sentinel" not in str(err.value)
    assert "upstream detail" not in str(err.value)


def test_malformed_json_is_mapped_to_safe_gateway_error(monkeypatch):
    class InvalidJSONResponse(FakeResponse):
        def read(self):
            return b"{not-json"

    monkeypatch.setattr(
        gateway.urllib.request, "urlopen", lambda request, timeout=None: InvalidJSONResponse({})
    )
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("GET", "workflows?limit=1")
    assert err.value.status == 502
    assert "test-secret-sentinel" not in str(err.value)


def test_unverified_write_endpoint_is_rejected_without_network(monkeypatch):
    calls = []
    monkeypatch.setattr(gateway.urllib.request, "urlopen", lambda *a, **kw: calls.append(a))
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("POST", "workflows", {"name": "must-not-be-created"})
    assert err.value.status == 501
    assert calls == []


@pytest.mark.parametrize(
    ("upstream_status", "expected_status"),
    [(403, 403), (404, 404), (500, 502), (503, 502)],
)
def test_upstream_statuses_map_to_safe_errors(monkeypatch, upstream_status, expected_status):
    def fail(request, timeout=None):
        raise gateway.urllib.error.HTTPError(
            request.full_url, upstream_status, "test-secret-sentinel", {}, None
        )

    monkeypatch.setattr(gateway.urllib.request, "urlopen", fail)
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("GET", "workflows?limit=1")
    assert err.value.status == expected_status
    assert "test-secret-sentinel" not in str(err.value)


def test_network_error_is_sanitized(monkeypatch):
    def fail(request, timeout=None):
        raise gateway.urllib.error.URLError("test-secret-sentinel host failure")

    monkeypatch.setattr(gateway.urllib.request, "urlopen", fail)
    monkeypatch.setattr(gateway, "KEY_FILE", Path("/tmp/cknexus-test-api-key"))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: "test-secret-sentinel")
    with pytest.raises(gateway.N8NAPIError) as err:
        gateway.n8n_request("GET", "workflows?limit=1")
    assert err.value.status == 504
    assert "test-secret-sentinel" not in str(err.value)
