from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.universal_builder_connector import (
    AuthorizationRequired,
    UniversalBuilderConnector,
    UnsupportedOperation,
)

REGISTRY = Path(__file__).resolve().parents[1] / "config" / "uabc_platform_registry.json"


def test_registry_loads_unique_platforms_and_known_statuses():
    connector = UniversalBuilderConnector(REGISTRY)
    result = connector.discover_platforms()
    assert result.status == "PASS"
    assert result.data["count"] >= 35
    ids = [entry["id"] for entry in result.data["platforms"]]
    assert len(ids) == len(set(ids))
    assert {"base44", "lovable", "github", "ollama", "wdotech", "suriya_ai"} <= set(ids)


def test_registry_rejects_duplicate_ids_and_bad_status(tmp_path):
    source = json.loads(REGISTRY.read_text(encoding="utf-8"))
    source["platforms"].append(dict(source["platforms"][0]))
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        UniversalBuilderConnector(duplicate_path)

    source["platforms"].pop()
    source["platforms"][0]["status"] = "CONNECTED"
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid UABC status"):
        UniversalBuilderConnector(invalid_path)


def test_registry_results_do_not_claim_accounts_connected():
    connector = UniversalBuilderConnector(REGISTRY)
    result = connector.check_connection("lovable")
    assert result.status == "NOT_TESTED"
    assert result.data["live_test"] == "NOT_TESTED"
    assert result.data["ui_state"] == "DISCONNECTED"


def test_unsupported_write_is_explicit_and_requires_confirmation():
    connector = UniversalBuilderConnector(REGISTRY)
    no_confirmation = connector.execute("github", "deploy_project")
    assert no_confirmation.status == "CONFIRMATION_REQUIRED"
    unsupported = connector.execute("lovable", "deploy_project", confirmed=True)
    assert unsupported.status == "UNSUPPORTED_OPERATION"


def test_unknown_operation_is_rejected():
    connector = UniversalBuilderConnector(REGISTRY)
    with pytest.raises(ValueError, match="Unknown UABC operation"):
        connector.execute("github", "delete_everything")


def test_outbound_kill_switch_blocks_health_check():
    connector = UniversalBuilderConnector(REGISTRY)
    connector.disable_outbound()

    class Adapter:
        capabilities = {"check_connection"}

        def check_connection(self):
            return {"connected": True}

        def execute(self, operation, **kwargs):
            return {"ok": True}

    connector.register_adapter("github", Adapter())
    result = connector.check_connection("github")
    assert result.status == "BLOCKED"


def test_adapter_secrets_are_redacted_and_errors_do_not_leak():
    connector = UniversalBuilderConnector(REGISTRY)

    class Adapter:
        capabilities = {"get_usage"}

        def __init__(self):
            self.api_key = "super-secret"

        def check_connection(self):
            return {
                "connected": True,
                "api_key": self.api_key,
                "message": f"connected with {self.api_key}",
                "account": "demo",
            }

        def execute(self, operation, **kwargs):
            raise RuntimeError("authorization=Bearer super-secret")

    connector.register_adapter("github", Adapter())
    healthy = connector.check_connection("github")
    assert healthy.status == "PASS"
    assert healthy.data["details"]["api_key"] == "[REDACTED]"
    assert "super-secret" not in json.dumps(healthy.as_dict())
    failed = connector.execute("github", "get_usage")
    assert failed.status == "FAIL"
    assert "super-secret" not in json.dumps(failed.as_dict())


def test_adapter_auth_and_unsupported_exceptions_are_normalized():
    connector = UniversalBuilderConnector(REGISTRY)

    class AuthAdapter:
        capabilities = {"get_usage"}

        def check_connection(self):
            return {"connected": False}

        def execute(self, operation, **kwargs):
            raise AuthorizationRequired("do not expose this detail")

    connector.register_adapter("github", AuthAdapter())
    assert connector.execute("github", "get_usage").status == "BLOCKED_AUTH"

    class UnsupportedAdapter(AuthAdapter):
        def execute(self, operation, **kwargs):
            raise UnsupportedOperation("not available")

    connector.register_adapter("github", UnsupportedAdapter())
    assert connector.execute("github", "get_usage").status == "UNSUPPORTED_OPERATION"


def test_search_filter_is_case_insensitive():
    connector = UniversalBuilderConnector(REGISTRY)
    result = connector.discover_platforms(query="THAILAND")
    names = {item["id"] for item in result.data["platforms"]}
    assert {"wdotech", "appgu", "suriya_ai"} <= names


def test_connection_check_reports_auth_blocked_when_adapter_requires_authorization():
    connector = UniversalBuilderConnector(REGISTRY)

    class AuthAdapter:
        capabilities = {"check_connection"}

        def check_connection(self):
            raise AuthorizationRequired("secret provider response")

        def execute(self, operation, **kwargs):
            raise AuthorizationRequired("secret provider response")

    connector.register_adapter("github", AuthAdapter())
    result = connector.check_connection("github")
    assert result.status == "BLOCKED_AUTH"
    assert result.data["ui_state"] == "AUTH_REQUIRED"
    assert "secret provider response" not in json.dumps(result.as_dict())
