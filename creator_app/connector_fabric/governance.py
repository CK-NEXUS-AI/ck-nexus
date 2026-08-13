from __future__ import annotations

from collections.abc import Callable
from typing import Any

from creator_app.connector_fabric.fabric import ToolAuthorizationDecision
from creator_app.connector_fabric.models import ConnectorRecord, NormalizedTool, RiskClass
from creator_app.council_authority.authority import CapabilityAuthority, PolicyDenied
from creator_app.council_authority.identity import CallerIdentity

CapabilityMapper = Callable[[ConnectorRecord, NormalizedTool], str]


def capability_id_for_tool(connector: ConnectorRecord, tool: NormalizedTool) -> str:
    """Return the deterministic policy capability for a verified connector tool."""
    return f"connector.{connector.config.connector_id}.{tool.name}"


def authority_params(
    connector: ConnectorRecord,
    tool: NormalizedTool,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Build the exact parameter object bound into a one-time execution grant."""
    return {
        "connector_id": connector.config.connector_id,
        "tool": tool.name,
        "risk": tool.risk.value,
        "schema_hash": connector.schema_hash,
        "arguments": arguments,
    }


class CapabilityAuthorityToolAuthorizer:
    """Adapter from Connector Fabric authorization to CapabilityAuthority.

    The adapter is intentionally not installed by default. ConnectorFabric keeps
    FailClosedAuthorizer unless a trusted runtime explicitly injects this adapter.
    A policy grant is consumed before MCP execution, so a failed/ambiguous tool
    call cannot reuse the same authorization grant.
    """

    _ALLOWED_CONTEXT_FIELDS = (
        "taskId",
        "evidenceRef",
        "evidenceRefs",
        "confirmation",
    )

    def __init__(
        self,
        authority: CapabilityAuthority,
        *,
        capability_mapper: CapabilityMapper = capability_id_for_tool,
    ) -> None:
        self.authority = authority
        self.capability_mapper = capability_mapper

    def authorize(
        self,
        *,
        connector: ConnectorRecord,
        tool: NormalizedTool,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolAuthorizationDecision:
        identity = context.get("identity")
        if not isinstance(identity, CallerIdentity):
            return ToolAuthorizationDecision(False, "Trusted caller identity is required.")
        if tool.risk is RiskClass.UNKNOWN:
            return ToolAuthorizationDecision(False, "Unknown-risk connector tools are denied.")

        capability_id = self.capability_mapper(connector, tool)
        params = authority_params(connector, tool, arguments)
        authority_context = {
            key: context[key]
            for key in self._ALLOWED_CONTEXT_FIELDS
            if key in context
        }
        try:
            decision = self.authority.enforce(
                identity,
                capability_id,
                params,
                authority_context,
            )
        except PolicyDenied as exc:
            return ToolAuthorizationDecision(False, f"Policy denied: {exc.code}.")
        except (KeyError, TypeError, ValueError):
            return ToolAuthorizationDecision(False, "Policy authority rejected the request.")

        grant = decision.get("executionGrant")
        if not isinstance(grant, dict):
            return ToolAuthorizationDecision(False, "Policy authority did not issue a valid grant.")
        if not self.authority.consume_grant(identity, grant, params):
            return ToolAuthorizationDecision(False, "Execution grant could not be consumed.")
        return ToolAuthorizationDecision(True, "One-time policy grant consumed.")
