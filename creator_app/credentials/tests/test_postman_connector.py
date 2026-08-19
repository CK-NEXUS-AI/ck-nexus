"""Tests สำหรับ Postman Connector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from creator_app.credentials.postman_connector import (
    PostmanCollection,
    PostmanConnector,
    PostmanEnvironment,
)


class TestPostmanCollection:
    def test_creation(self):
        c = PostmanCollection(uid="123", name="My API")
        assert c.uid == "123"
        assert c.name == "My API"


class TestPostmanEnvironment:
    def test_creation(self):
        e = PostmanEnvironment(uid="456", name="Production")
        assert e.uid == "456"
        assert e.name == "Production"


class TestPostmanConnector:
    def test_init_requires_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="POSTMAN_API_KEY not found"):
                PostmanConnector()

    def test_init_with_key(self):
        connector = PostmanConnector(api_key="test-key-123")
        assert connector._api_key == "test-key-123"

    @patch("creator_app.credentials.postman_connector.requests.get")
    def test_list_collections(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "collections": [
                {
                    "uid": "abc-123",
                    "info": {
                        "name": "Test Collection",
                        "description": "A test",
                        "owner": "user1",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        connector = PostmanConnector(api_key="test-key")
        collections = connector.list_collections()

        assert len(collections) == 1
        assert collections[0].name == "Test Collection"
        assert collections[0].uid == "abc-123"

    @patch("creator_app.credentials.postman_connector.requests.get")
    def test_list_environments(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "environments": [
                {"uid": "env-1", "name": "Dev", "values": []}
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        connector = PostmanConnector(api_key="test-key")
        envs = connector.list_environments()

        assert len(envs) == 1
        assert envs[0].name == "Dev"

    @patch("creator_app.credentials.postman_connector.requests.post")
    def test_create_collection(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"collection": {"uid": "new-123"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        connector = PostmanConnector(api_key="test-key")
        result = connector.create_collection("New API", "Description")

        assert "collection" in result
        mock_post.assert_called_once()

    @patch("creator_app.credentials.postman_connector.requests.get")
    def test_status_connected(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"workspaces": [{"id": "w1"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        connector = PostmanConnector(api_key="test-key")
        status = connector.status()
        assert status["connected"] is True

    @patch("creator_app.credentials.postman_connector.requests.get")
    def test_status_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        connector = PostmanConnector(api_key="test-key")
        status = connector.status()
        assert status["connected"] is False
        assert "error" in status
