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
