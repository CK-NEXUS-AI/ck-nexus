from __future__ import annotations

import sys
from types import SimpleNamespace

from scripts import test_openai_live


def test_expired_openai_credential_is_reported_as_blocked(monkeypatch, capsys):
    class AuthenticationError(Exception):
        pass

    class Responses:
        @staticmethod
        def create(**_kwargs):
            raise AuthenticationError("expired_secret_key")

    class Client:
        def __init__(self):
            self.responses = Responses()

    fake_openai = SimpleNamespace(
        AuthenticationError=AuthenticationError,
        OpenAI=Client,
    )
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_SMOKE_MODEL", "gpt-5-mini")

    assert test_openai_live.main() == 2
    assert "BLOCKED" in capsys.readouterr().out


def test_live_smoke_requires_an_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert test_openai_live.main() == 2
    assert "OPENAI_API_KEY is not configured" in capsys.readouterr().out
