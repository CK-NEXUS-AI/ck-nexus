from __future__ import annotations

import json

import pytest

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.pinterest_api import PinterestAPIClient, PinterestAPIError


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def _client(token: str = "pina-pinterest-secret"):
    broker = CredentialBroker(environment={CredentialId.PINTEREST_ACCESS_TOKEN: token})
    return PinterestAPIClient(broker)


def test_status_is_read_only_and_secret_redacted():
    result = _client().status()
    assert result["configured"] is True
    assert result["required_scopes"] == ["boards:read", "pins:read"]
    assert result["write_operations_available"] is False
    assert result["image_downloads"] is False
    assert "pina-pinterest-secret" not in repr(result)


def test_missing_token_fails_closed():
    client = PinterestAPIClient(CredentialBroker())
    with pytest.raises(PinterestAPIError, match="unavailable"):
        client.list_board_pins(board_id="123456", limit=10)


@pytest.mark.parametrize(("board_id", "limit"), [("../x", 10), ("", 10), ("123", 501), ("123", 0)])
def test_invalid_collection_request_is_rejected(board_id, limit):
    with pytest.raises(ValueError):
        _client().list_board_pins(board_id=board_id, limit=limit)


def test_list_board_pins_paginates_and_returns_only_metadata(monkeypatch):
    import creator_app.pinterest_api as module

    calls = []

    def fake_request(request, *, trusted_hosts, timeout):
        calls.append(
            (
                request.full_url,
                request.get_method(),
                trusted_hosts,
                request.get_header("Authorization"),
            )
        )
        if len(calls) == 1:
            body = {
                "items": [
                    {
                        "id": str(i),
                        "title": f"Pin {i}",
                        "description": "design reference",
                        "board_id": "123456",
                        "media": {
                            "media_type": "image",
                            "images": {"1200x": {"url": f"https://i.pinimg.com/1200x/{i}.jpg"}},
                        },
                    }
                    for i in range(250)
                ],
                "bookmark": "cursor-next",
            }
        else:
            body = {
                "items": [
                    {
                        "id": str(i),
                        "title": f"Pin {i}",
                        "media": {
                            "images": {"1200x": {"url": f"https://i.pinimg.com/1200x/{i}.jpg"}}
                        },
                    }
                    for i in range(250, 300)
                ],
                "bookmark": None,
            }
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr(module, "open_trusted_request", fake_request)
    result = _client().list_board_pins(board_id="123456", limit=300)

    assert result["count"] == 300
    assert result["page_count"] == 2
    assert result["more_available"] is False
    assert result["image_bytes_downloaded"] == 0
    assert result["write_operations_performed"] is False
    assert len(calls) == 2
    assert all(x[1] == "GET" and x[2] == {"api.pinterest.com"} for x in calls)
    assert all(x[3] == "Bearer pina-pinterest-secret" for x in calls)
    assert "bookmark=cursor-next" in calls[1][0]
    assert result["items"][0]["pin_url"] == "https://www.pinterest.com/pin/0/"
    assert result["items"][0]["image_url"] == "https://i.pinimg.com/1200x/0.jpg"
    assert result["items"][0]["rights_status"] == "unknown"
    assert result["items"][0]["reusable"] is False
    assert "pina-pinterest-secret" not in repr(result)


def test_image_url_from_untrusted_host_is_not_retained(monkeypatch):
    import creator_app.pinterest_api as module

    body = {
        "items": [
            {
                "id": "999",
                "media": {"images": {"1200x": {"url": "https://attacker.example/x.jpg"}}},
            }
        ],
        "bookmark": None,
    }
    monkeypatch.setattr(
        module,
        "open_trusted_request",
        lambda *_args, **_kwargs: FakeResponse(json.dumps(body).encode()),
    )
    result = _client().list_board_pins(board_id="123456", limit=1)
    assert result["items"][0]["image_url"] is None


def test_environment_binding_is_scoped_to_pinterest_consumer(monkeypatch):
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "pina-env-secret")
    broker = CredentialBroker.from_environment()
    assert broker.is_allowed(CredentialId.PINTEREST_ACCESS_TOKEN, consumer="pinterest.api")
    assert not broker.is_allowed(CredentialId.PINTEREST_ACCESS_TOKEN, consumer="github.app")
    assert "pina-env-secret" not in repr(broker.statuses(consumer="pinterest.api"))
