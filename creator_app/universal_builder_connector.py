"""Universal AI Builder Connector (UABC) registry and capability-safe operation facade.

This module deliberately does not infer account connectivity from public documentation.
Provider-specific authenticated adapters can be registered as they are implemented.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "uabc_platform_registry.json"
VALID_PLATFORM_STATUSES = frozenset(
    {
        "SUPPORTED_API",
        "SUPPORTED_OAUTH",
        "SUPPORTED_MCP",
        "SUPPORTED_CLI",
        "SUPPORTED_WEBHOOK",
        "BROWSER_AUTOMATION_ONLY",
        "MANUAL_SETUP_REQUIRED",
        "RESEARCH_REQUIRED",
        "UNAVAILABLE",
        "BLOCKED_AUTH",
        "BLOCKED_BY_PLAN",
    }
)
UI_STATES = frozenset({"CONNECTED", "AUTH_REQUIRED", "DEGRADED", "UNSUPPORTED", "DISCONNECTED"})
READ_ONLY_OPERATIONS = frozenset(
    {
        "discover_platforms",
        "get_platform_details",
        "get_supported_capabilities",
        "check_connection",
        "list_projects",
        "get_project",
        "get_usage",
        "get_deployment_status",
    }
)
MUTATING_OPERATIONS = frozenset(
    {
        "begin_authorization",
        "complete_authorization",
        "create_project",
        "update_project",
        "export_project",
        "deploy_project",
        "disconnect_platform",
    }
)
ALL_OPERATIONS = READ_ONLY_OPERATIONS | MUTATING_OPERATIONS


class UABCError(ValueError):
    """Base error for explicit UABC operation failures."""


class UnsupportedOperation(UABCError):
    """Raised when an operation is not declared by the provider adapter."""


class AuthorizationRequired(UABCError):
    """Raised when an operation requires credentials not available to the adapter."""


class PlatformAdapter(Protocol):
    """Minimal contract for provider-specific adapters."""

    def check_connection(self) -> dict[str, Any]: ...

    def execute(self, operation: str, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: str
    operation: str
    platform_id: str | None
    message: str
    data: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "operation": self.operation,
            "platform_id": self.platform_id,
            "message": self.message,
            "data": self.data or {},
        }


class ExistingGitHubStatusAdapter:
    """Reuse the existing CK-NEXUS GitHub integration for a read-only live status check."""

    capabilities = frozenset({"check_connection"})

    def __init__(self, integration: Any) -> None:
        self.integration = integration

    def check_connection(self) -> dict[str, Any]:
        status = self.integration.status().as_dict()
        if status.get("configured") is not True:
            raise AuthorizationRequired("GitHub credential is not configured.")
        return {
            **status,
            "connected": status.get("connected") is True
            and status.get("repository_access") is True,
        }

    def execute(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        if operation != "check_connection":
            raise UnsupportedOperation("Existing GitHub adapter is read-only.")
        return self.check_connection()


class UniversalBuilderConnector:
    """Read-only registry with capability-gated, fail-closed adapter dispatch."""

    def __init__(self, registry_path: str | Path = REGISTRY_PATH) -> None:
        self.registry_path = Path(registry_path)
        self._platforms = self._load_registry(self.registry_path)
        self._adapters: dict[str, PlatformAdapter] = {}
        self._disabled = os.getenv("UABC_KILL_SWITCH", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @staticmethod
    def _load_registry(path: Path) -> dict[str, dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("UABC registry must be a schema_version=1 object.")
        entries = payload.get("platforms")
        if not isinstance(entries, list):
            raise ValueError("UABC registry platforms must be a list.")
        platforms: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Each UABC platform entry must be an object.")
            platform_id = entry.get("id")
            if not isinstance(platform_id, str) or not platform_id or platform_id in platforms:
                raise ValueError("UABC platform IDs must be unique non-empty strings.")
            if entry.get("status") not in VALID_PLATFORM_STATUSES:
                raise ValueError(f"Invalid UABC status for platform {platform_id}.")
            if not isinstance(entry.get("capabilities", []), list):
                raise ValueError(f"Capabilities for platform {platform_id} must be a list.")
            if not isinstance(entry.get("official_url"), str) or not entry[
                "official_url"
            ].startswith("https://"):
                raise ValueError(f"Platform {platform_id} requires an HTTPS official_url.")
            # Copy records so callers cannot mutate internal state.
            platforms[platform_id] = json.loads(json.dumps(entry))
        return platforms

    def register_adapter(self, platform_id: str, adapter: PlatformAdapter) -> None:
        if platform_id not in self._platforms:
            raise KeyError(f"Unknown UABC platform: {platform_id}")
        self._adapters[platform_id] = adapter

    def disable_outbound(self) -> None:
        """Process-local kill switch; callers can also set UABC_KILL_SWITCH=true."""
        self._disabled = True

    def enable_outbound(self) -> None:
        """Re-enable outbound operations only when the environment kill switch is unset."""
        if os.getenv("UABC_KILL_SWITCH", "false").strip().lower() in {"1", "true", "yes", "on"}:
            raise UABCError("UABC_KILL_SWITCH environment override must be removed by an operator.")
        self._disabled = False

    def discover_platforms(
        self, *, query: str | None = None, status: str | None = None
    ) -> OperationResult:
        if status is not None and status not in VALID_PLATFORM_STATUSES:
            raise ValueError("Unknown platform status filter.")
        normalized_query = query.casefold().strip() if query else None
        items = []
        for entry in self._platforms.values():
            if status and entry["status"] != status:
                continue
            if (
                normalized_query
                and normalized_query not in json.dumps(entry, ensure_ascii=False).casefold()
            ):
                continue
            items.append(self._public_record(entry))
        return OperationResult(
            "PASS",
            "discover_platforms",
            None,
            "Registry discovery completed; this does not imply account connectivity.",
            {"count": len(items), "platforms": items},
        )

    def get_platform_details(self, platform_id: str) -> OperationResult:
        entry = self._platforms.get(platform_id)
        if entry is None:
            return OperationResult(
                "UNAVAILABLE",
                "get_platform_details",
                platform_id,
                "Platform is not present in the registry.",
            )
        return OperationResult(
            "PASS",
            "get_platform_details",
            platform_id,
            "Platform metadata loaded from local registry.",
            self._public_record(entry),
        )

    def get_supported_capabilities(self, platform_id: str) -> OperationResult:
        entry = self._platforms.get(platform_id)
        if entry is None:
            return OperationResult(
                "UNAVAILABLE",
                "get_supported_capabilities",
                platform_id,
                "Platform is not present in the registry.",
            )
        adapter = self._adapters.get(platform_id)
        return OperationResult(
            "PASS",
            "get_supported_capabilities",
            platform_id,
            "Capabilities are documentation metadata; only adapter capabilities are executable.",
            {
                "documented_capabilities": list(entry.get("capabilities", [])),
                "implemented_capabilities": sorted(getattr(adapter, "capabilities", ()))
                if adapter
                else [],
                "adapter_registered": adapter is not None,
            },
        )

    def check_connection(self, platform_id: str) -> OperationResult:
        entry = self._platforms.get(platform_id)
        if entry is None:
            return OperationResult(
                "UNAVAILABLE",
                "check_connection",
                platform_id,
                "Platform is not present in the registry.",
            )
        adapter = self._adapters.get(platform_id)
        if adapter is None:
            return OperationResult(
                "NOT_TESTED",
                "check_connection",
                platform_id,
                "No runtime adapter is registered; no live connection was attempted.",
                {
                    "ui_state": "DISCONNECTED",
                    "registry_status": entry["status"],
                    "auth_required": entry.get("auth_required", True),
                    "adapter_registered": False,
                    "live_test": "NOT_TESTED",
                },
            )
        if self._disabled:
            return OperationResult(
                "BLOCKED",
                "check_connection",
                platform_id,
                "UABC outbound kill switch is enabled.",
                {"ui_state": "DISCONNECTED", "live_test": "NOT_TESTED"},
            )
        try:
            result = adapter.check_connection()
        except AuthorizationRequired:
            return OperationResult(
                "BLOCKED_AUTH",
                "check_connection",
                platform_id,
                "Provider authorization is required.",
                {"ui_state": "AUTH_REQUIRED", "live_test": "FAIL"},
            )
        except Exception:  # suppress adapter exception details to protect secrets
            return OperationResult(
                "FAIL",
                "check_connection",
                platform_id,
                "Adapter health check failed; sensitive exception details were suppressed.",
                {"ui_state": "DEGRADED", "live_test": "FAIL"},
            )
        connected = result.get("connected") is True
        return OperationResult(
            "PASS" if connected else "FAIL",
            "check_connection",
            platform_id,
            "Authenticated connection verified."
            if connected
            else "Adapter did not verify an authenticated connection.",
            {
                "ui_state": "CONNECTED" if connected else "DEGRADED",
                "live_test": "PASS" if connected else "FAIL",
                "details": self._redact(result, self._adapter_secrets(adapter)),
            },
        )

    def execute(self, platform_id: str, operation: str, **kwargs: Any) -> OperationResult:
        if operation not in ALL_OPERATIONS:
            raise ValueError("Unknown UABC operation.")
        if operation == "discover_platforms":
            return self.discover_platforms(**kwargs)
        if operation == "get_platform_details":
            return self.get_platform_details(platform_id)
        if operation == "get_supported_capabilities":
            return self.get_supported_capabilities(platform_id)
        if operation == "check_connection":
            return self.check_connection(platform_id)
        entry = self._platforms.get(platform_id)
        if entry is None:
            return OperationResult(
                "UNAVAILABLE", operation, platform_id, "Platform is not present in the registry."
            )
        if operation in MUTATING_OPERATIONS and kwargs.pop("confirmed", False) is not True:
            return OperationResult(
                "CONFIRMATION_REQUIRED",
                operation,
                platform_id,
                "This operation may modify state and requires explicit confirmation.",
            )
        adapter = self._adapters.get(platform_id)
        if adapter is None:
            return OperationResult(
                "UNSUPPORTED_OPERATION",
                operation,
                platform_id,
                "No provider-specific adapter is implemented; operation was not simulated.",
            )
        if self._disabled:
            return OperationResult(
                "BLOCKED", operation, platform_id, "UABC outbound kill switch is enabled."
            )
        implemented = set(getattr(adapter, "capabilities", ()))
        if operation not in implemented:
            return OperationResult(
                "UNSUPPORTED_OPERATION",
                operation,
                platform_id,
                "The registered adapter does not declare this capability.",
            )
        try:
            result = adapter.execute(operation, **kwargs)
        except AuthorizationRequired:
            return OperationResult(
                "BLOCKED_AUTH", operation, platform_id, "Provider authorization is required."
            )
        except UnsupportedOperation:
            return OperationResult(
                "UNSUPPORTED_OPERATION",
                operation,
                platform_id,
                "The provider does not support this operation.",
            )
        except Exception:
            return OperationResult(
                "FAIL",
                operation,
                platform_id,
                "Provider operation failed; sensitive exception details were suppressed.",
            )
        return OperationResult(
            "PASS",
            operation,
            platform_id,
            "Provider adapter returned a result.",
            self._redact(result, self._adapter_secrets(adapter)),
        )

    @staticmethod
    def _adapter_secrets(adapter: PlatformAdapter) -> tuple[str, ...]:
        sensitive_fragments = (
            "token",
            "secret",
            "password",
            "api_key",
            "apikey",
            "credential",
            "cookie",
        )
        values = getattr(adapter, "__dict__", {})
        return tuple(
            value
            for key, value in values.items()
            if isinstance(value, str)
            and value
            and any(part in key.casefold() for part in sensitive_fragments)
        )

    @staticmethod
    def _redact(value: Any, known_secrets: tuple[str, ...] = ()) -> Any:
        sensitive_fragments = (
            "token",
            "secret",
            "password",
            "api_key",
            "apikey",
            "authorization",
            "credential",
            "cookie",
        )
        if isinstance(value, dict):
            return {
                str(key): "[REDACTED]"
                if any(part in str(key).casefold() for part in sensitive_fragments)
                else UniversalBuilderConnector._redact(item, known_secrets)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [UniversalBuilderConnector._redact(item, known_secrets) for item in value]
        if isinstance(value, str):
            redacted = value
            for secret in known_secrets:
                redacted = redacted.replace(secret, "[REDACTED]")
            return redacted[:2000]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return str(type(value).__name__)

    @staticmethod
    def _public_record(entry: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(entry))


_default_connector: UniversalBuilderConnector | None = None


def get_uabc() -> UniversalBuilderConnector:
    global _default_connector
    if _default_connector is None:
        _default_connector = UniversalBuilderConnector()
    return _default_connector
