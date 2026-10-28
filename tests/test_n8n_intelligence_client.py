from pathlib import Path

import pytest

from creator_app.n8n_intelligence.client import N8NReadClient, N8NReadError


def test_client_rejects_non_http_base_url(tmp_path: Path):
    with pytest.raises(ValueError):
        N8NReadClient("file:///tmp", tmp_path / "key")


def test_client_requires_key_file(tmp_path: Path):
    client = N8NReadClient("http://127.0.0.1:5678", tmp_path / "missing")
    with pytest.raises(N8NReadError):
        client.list_executions()


def test_401_opens_persistent_circuit_and_prevents_followup_request(tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    from creator_app.n8n_intelligence.circuit_breaker import PersistentCircuitBreaker

    key_file = tmp_path / "key"
    key_file.write_text("test-key")
    breaker = PersistentCircuitBreaker(tmp_path / "circuit.json")
    calls = []

    def unauthorized(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", unauthorized)
    client = N8NReadClient("http://127.0.0.1:5678/api/v1", key_file, circuit_breaker=breaker)
    with pytest.raises(N8NReadError, match="HTTP error 401"):
        client.list_executions()
    with pytest.raises(N8NReadError, match="circuit open"):
        client.list_executions()
    assert len(calls) == 1
    assert breaker.snapshot()["status"] == "open"
