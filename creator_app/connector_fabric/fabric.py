from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from creator_app.connector_fabric.evidence import ConnectorEvidenceLedger
from creator_app.connector_fabric.mcp import MCPClient
from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorProtocol,
    ConnectorRecord,
    ConnectorState,
    NormalizedTool,
    RiskClass,
)
from creator_app.connector_fabric.openapi import OpenAPIClient
from creator_app.connector_fabric.registry import ConnectorRegistry
from creator_app.connector_fabric.security import EndpointPolicy, validate_endpoint


@dataclass(frozen=True, slots=True)
class ToolAuthorizationDecision:
    allowed: bool
    reason: str


class ToolAuthorizer(Protocol):
    def authorize(
        self,
        *,
        connector: ConnectorRecord,
        tool: NormalizedTool,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolAuthorizationDecision: ...


class FailClosedAuthorizer:
    def authorize(self, **kwargs) -> ToolAuthorizationDecision:  # noqa: ANN003
        return ToolAuthorizationDecision(False, "No trusted execution authorizer is configured.")


class ConnectorFabric:
    """Dynamic discovery and model-neutral binding with fail-closed execution."""

    def __init__(
        self,
        *,
        registry: ConnectorRegistry,
        evidence: ConnectorEvidenceLedger,
        mcp_client: MCPClient | None = None,
        openapi_client: OpenAPIClient | None = None,
        authorizer: ToolAuthorizer | None = None,
    ) -> None:
        self.registry = registry
        self.evidence = evidence
        self.mcp_client = mcp_client or MCPClient()
        self.openapi_client = openapi_client or OpenAPIClient()
        self.authorizer = authorizer or FailClosedAuthorizer()

    def register(self, config: ConnectorConfig) -> ConnectorRecord:
        validate_endpoint(
            config.url,
            policy=EndpointPolicy(allow_private_network=config.allow_private_network),
        )
        record = self.registry.register(config)
        self.evidence.append(
            "connector.registered",
            config.connector_id,
            {"protocol": config.protocol.value, "trustSource": config.trust_source, "credentialRef": config.credential_ref},
        )
        return record

    def discover(self, connector_id: str) -> ConnectorRecord:
        record = self.registry.get(connector_id)
        try:
            if record.config.protocol is ConnectorProtocol.MCP:
                snapshot = self.mcp_client.discover(record.config)
            elif record.config.protocol is ConnectorProtocol.OPENAPI:
                snapshot = self.openapi_client.discover(record.config)
            else:
                raise RuntimeError("Unsupported connector protocol.")
        except Exception as exc:
            blocked = self.registry.set_state(connector_id, ConnectorState.BLOCKED, blocked_reason=type(exc).__name__)
            self.evidence.append(
                "connector.discovery_blocked",
                connector_id,
                {"errorType": type(exc).__name__, "message": str(exc)[:300]},
            )
            raise
        updated = self.registry.set_snapshot(snapshot)
        self.evidence.append(
            "connector.schema_verified",
            connector_id,
            {
                "schemaHash": snapshot.schema_hash,
                "toolCount": len(snapshot.tools),
                "rejectedToolCount": len(snapshot.rejected_tools),
                "protocolVersion": snapshot.protocol_version,
            },
        )
        return updated

    def activate(self, connector_id: str, *, allow_write: bool = False) -> ConnectorRecord:
        record = self.registry.get(connector_id)
        snapshot = self.registry.snapshot(connector_id)
        if record.state is not ConnectorState.SCHEMA_VERIFIED:
            raise RuntimeError("Connector must pass schema verification before activation.")
        has_non_read = any(tool.risk is not RiskClass.READ_ONLY for tool in snapshot.tools)
        if allow_write:
            state = ConnectorState.ACTIVE_WRITE
        else:
            state = ConnectorState.ACTIVE_READ_ONLY
            if has_non_read:
                # Non-read tools stay registered but are withheld from model binding.
                pass
        updated = self.registry.set_state(connector_id, state)
        self.evidence.append(
            "connector.activated",
            connector_id,
            {"mode": state.value, "schemaHash": snapshot.schema_hash},
        )
        return updated

    def model_tools(self, connector_id: str) -> tuple[dict[str, Any], ...]:
        record = self.registry.get(connector_id)
        if record.state not in {ConnectorState.ACTIVE_READ_ONLY, ConnectorState.ACTIVE_WRITE}:
            return ()
        snapshot = self.registry.snapshot(connector_id)
        exposed: list[dict[str, Any]] = []
        for tool in snapshot.tools:
            if record.state is ConnectorState.ACTIVE_READ_ONLY and not tool.read_only:
                continue
            exposed.append(
                {
                    "type": "function",
                    "name": tool.logical_name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                    "x-ck-risk": tool.risk.value,
                    "x-ck-schema-hash": snapshot.schema_hash,
                }
            )
        return tuple(exposed)

    def invoke(
        self,
        connector_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.registry.get(connector_id)
        if record.state not in {ConnectorState.ACTIVE_READ_ONLY, ConnectorState.ACTIVE_WRITE}:
            raise PermissionError("Connector is not active.")
        snapshot = self.registry.snapshot(connector_id)
        tool = next((item for item in snapshot.tools if item.name == tool_name), None)
        if tool is None:
            raise KeyError("Tool is not present in the verified connector snapshot.")
        if record.state is ConnectorState.ACTIVE_READ_ONLY and not tool.read_only:
            raise PermissionError("Write-capable tool is not active.")
        decision = self.authorizer.authorize(
            connector=record,
            tool=tool,
            arguments=arguments,
            context=context or {},
        )
        if not decision.allowed:
            self.evidence.append(
                "connector.execution_denied",
                connector_id,
                {"tool": tool.name, "risk": tool.risk.value, "reason": decision.reason[:200]},
            )
            raise PermissionError("Connector execution denied by policy authority.")
        if record.config.protocol is not ConnectorProtocol.MCP:
            raise RuntimeError("OpenAPI execution is not enabled in this release; discovery/binding only.")
        result = self.mcp_client.call_tool(record.config, tool, arguments)
        self.evidence.append(
            "connector.execution_completed",
            connector_id,
            {"tool": tool.name, "risk": tool.risk.value, "schemaHash": snapshot.schema_hash},
        )
        return result
