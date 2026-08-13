from __future__ import annotations

import json
import re
from typing import Any

from creator_app.connector_fabric.evidence import sha256_json
from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorProtocol,
    DiscoverySnapshot,
    NormalizedTool,
)
from creator_app.connector_fabric.risk import classify_openapi_operation
from creator_app.connector_fabric.security import EndpointPolicy, validate_endpoint
from creator_app.connector_fabric.transport import HttpTransport, UrllibHttpTransport


class OpenAPIDiscoveryError(RuntimeError):
    pass


_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
_SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization", "x-api-key"}


class OpenAPIClient:
    def __init__(
        self, *, transport: HttpTransport | None = None, timeout_seconds: float = 8.0
    ) -> None:
        self.transport = transport or UrllibHttpTransport()
        self.timeout_seconds = timeout_seconds

    def discover(self, config: ConnectorConfig) -> DiscoverySnapshot:
        if config.protocol is not ConnectorProtocol.OPENAPI:
            raise ValueError("OpenAPI client received a non-OpenAPI connector")
        validate_endpoint(
            config.url, policy=EndpointPolicy(allow_private_network=config.allow_private_network)
        )
        response = self.transport.request(
            "GET",
            config.url,
            headers={"Accept": "application/json, application/yaml, text/yaml"},
            body=None,
            timeout=self.timeout_seconds,
        )
        if not 200 <= response.status < 300:
            raise OpenAPIDiscoveryError(f"OpenAPI document returned HTTP {response.status}.")
        spec = self._parse_spec(response.body)
        version = spec.get("openapi")
        if not isinstance(version, str) or not version.startswith("3."):
            raise OpenAPIDiscoveryError("Only OpenAPI 3.x documents are accepted.")
        paths = spec.get("paths")
        if not isinstance(paths, dict):
            raise OpenAPIDiscoveryError("OpenAPI document does not contain a paths object.")

        allowed = set(config.allowed_tools)
        tools: list[NormalizedTool] = []
        seen: set[str] = set()
        for path, path_item in paths.items():
            if not isinstance(path, str) or not isinstance(path_item, dict):
                continue
            for method in _METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                name = self._operation_name(method, path, operation, seen)
                if allowed and name not in allowed:
                    continue
                tool = self._normalize_operation(
                    config.connector_id, method, path, path_item, operation, name
                )
                tools.append(tool)
                seen.add(name)
        tools.sort(key=lambda item: item.name)
        snapshot_payload = {
            "openapi": version,
            "info": spec.get("info", {}),
            "tools": [tool.as_dict() for tool in tools],
        }
        return DiscoverySnapshot(
            connector_id=config.connector_id,
            protocol=ConnectorProtocol.OPENAPI,
            protocol_version=version,
            tools=tuple(tools),
            schema_hash=sha256_json(snapshot_payload),
            capabilities={"openapi": version},
        )

    @staticmethod
    def _parse_spec(body: bytes) -> dict[str, Any]:
        if len(body) > 4_000_000:
            raise OpenAPIDiscoveryError("OpenAPI document exceeds size limit.")
        text = body.decode("utf-8")
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            try:
                import yaml  # type: ignore
            except ImportError:
                raise OpenAPIDiscoveryError(
                    "YAML OpenAPI requires optional PyYAML support."
                ) from None
            value = yaml.safe_load(text)
        if not isinstance(value, dict):
            raise OpenAPIDiscoveryError("OpenAPI document root must be an object.")
        return value

    @staticmethod
    def _operation_name(method: str, path: str, operation: dict[str, Any], seen: set[str]) -> str:
        raw = operation.get("operationId")
        if not isinstance(raw, str) or not raw.strip():
            raw = f"{method}_{path}"
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw.strip()).strip("_")[:96] or "operation"
        candidate = name
        suffix = 2
        while candidate in seen:
            candidate = f"{name}_{suffix}"
            suffix += 1
        return candidate

    @classmethod
    def _normalize_operation(
        cls,
        connector_id: str,
        method: str,
        path: str,
        path_item: dict[str, Any],
        operation: dict[str, Any],
        name: str,
    ) -> NormalizedTool:
        properties: dict[str, Any] = {}
        required: list[str] = []
        parameters = []
        for source in (path_item.get("parameters", []), operation.get("parameters", [])):
            if isinstance(source, list):
                parameters.extend(item for item in source if isinstance(item, dict))
        for parameter in parameters:
            pname = parameter.get("name")
            location = parameter.get("in")
            schema = parameter.get("schema", {})
            if not isinstance(pname, str) or not isinstance(schema, dict):
                continue
            if location == "header" and pname.lower() in _SENSITIVE_HEADERS:
                continue
            properties[pname] = {**schema, "x-ck-location": location}
            if parameter.get("required") is True:
                required.append(pname)

        request_body = operation.get("requestBody")
        if isinstance(request_body, dict):
            content = request_body.get("content", {})
            if isinstance(content, dict):
                media = content.get("application/json")
                if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                    properties["body"] = media["schema"]
                    if request_body.get("required") is True:
                        required.append("body")

        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            input_schema["required"] = sorted(set(required))
        description = (
            operation.get("description") or operation.get("summary") or f"{method.upper()} {path}"
        )
        if not isinstance(description, str):
            description = f"{method.upper()} {path}"
        return NormalizedTool(
            connector_id=connector_id,
            name=name,
            description=description[:4_000],
            input_schema=input_schema,
            annotations={"openapiMethod": method.upper(), "openapiPath": path},
            risk=classify_openapi_operation(method, name),
            source_method=method.upper(),
            source_path=path,
        )
