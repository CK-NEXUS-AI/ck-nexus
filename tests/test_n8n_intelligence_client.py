from pathlib import Path

import pytest

from creator_app.n8n_intelligence.client import N8NReadClient, N8NReadError


def test_client_rejects_non_http_base_url(tmp_path: Path):
    with pytest.raises(ValueError):
        N8NReadClient("file:///tmp", tmp_path / "key")


def test_client_rejects_untrusted_http_and_embedded_credentials(tmp_path: Path):
    for url in (
        "http://example.com",
        "http://user:secret@127.0.0.1:5678",
        "https://example.com?token=secret",
        "https://example.com#fragment",
    ):
        with pytest.raises(ValueError):
            N8NReadClient(url, tmp_path / "key")


def test_client_requires_key_file(tmp_path: Path):
    client = N8NReadClient("http://127.0.0.1:5678", tmp_path / "missing")
    with pytest.raises(N8NReadError):
        client.list_executions()


def test_n8n_transport_does_not_follow_redirects():
    from urllib.request import Request

    from creator_app.n8n_intelligence.client import _NoRedirectHandler

    handler = _NoRedirectHandler()
    request = Request("https://n8n.example.test/api/v1/executions")
    assert (
        handler.redirect_request(
            request, None, 302, "Found", {}, "https://attacker.example.test/collect"
        )
        is None
    )
