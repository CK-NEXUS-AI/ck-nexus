from __future__ import annotations

from collections.abc import Callable
from typing import Any

from creator_app.connector_fabric.fabric import (
    ConnectorActivationDecision,
    ToolAuthorizationDecision,
)
from creator_app.connector_fabric.models import (
    ConnectorRecord,
    ConnectorState,
    DiscoverySnapshot,
    NormalizedTool,
    RiskClass,
)
from creator_app.council_authority.authority import CapabilityAuthority, PolicyDenied
from creator_app.council_authority.identity import CallerIdentity

CapabilityMapper = Callable[[ConnectorRecord, NormalizedTool], str]
ActivationCapabilityMapper = Callable[[ConnectorRecord], str]

_ALLOWED_CONTEXT_FIELDS = (
    "taskId",
    "evidenceRef",
    "evidenceRefs",
    "confirmation",
)


def capability_id_for_tool(connector: ConnectorRecord, tool: NormalizedTool) -> str:
    """Return the deterministic policy capability for a verified connector tool."""
    return f"connector.{connector.config.connector_id}.{tool.name}"


def capability_id_for_write_activation(connector: ConnectorRecord) -> str:
    """Return the policy capability required to expose non-read connector tools."""
    return f"connector.{connector.config.connector_id}.activate_write"


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


def write_activation_authority_params(
    connector: ConnectorRecord,
    snapshot: DiscoverySnapshot,
) -> dict[str, Any]:
    """Build the non-secret parameter object bound into a write-activation grant."""
    return {
        "connector_id": connector.config.connector_id,
        "requested_state": ConnectorState.ACTIVE_WRITE.value,
        "schema_hash": snapshot.schema_hash,
        "tool_count": len(snapshot.tools),
        "read_only_count": sum(tool.risk is RiskClass.READ_ONLY for tool in snapshot.tools),
        "write_count": sum(tool.risk is RiskClass.WRITE for tool in snapshot.tools),
        "destructive_count": sum(tool.risk is RiskClass.DESTRUCTIVE for tool in snapshot.tools),
        "unknown_count": sum(tool.risk is RiskClass.UNKNOWN for tool in snapshot.tools),
    }


def _authority_context(context: dict[str, Any]) -> dict[str, Any]:
    return {key: context[key] for key in _ALLOWED_CONTEXT_FIELDS if key in context}


class CapabilityAuthorityToolAuthorizer:
    """Adapter from Connector Fabric authorization to CapabilityAuthority.

    The adapter is intentionally not installed by default. ConnectorFabric keeps
    FailClosedAuthorizer unless a trusted runtime explicitly injects this adapter.
    A policy grant is consumed before MCP execution, so a failed/ambiguous tool
    call cannot reuse the same authorization grant.
    """

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
        try:
            decision = self.authority.enforce(
                identity,
                capability_id,
                params,
                _authority_context(context),
            )
        except PolicyDenied as exc:
            return ToolAuthorizationDecision(False, f"Policy denied: {exc.code}.")
        except (KeyError, TypeError, ValueError):
            return ToolAuthorizationDecision(False, "Policy authority rejected the request.")

        grant = decision.get("executionGrant")
        if not isinstance(grant, dict):
            return ToolAuthorizationDecision(False, "Policy authority did not issue a valid grant.")
        if not self.authority.consume_grant(identity, grant, params, expected_task_id=context.get("taskId")):
            return ToolAuthorizationDecision(False, "Execution grant could not be consumed.")
        return ToolAuthorizationDecision(True, "One-time policy grant consumed.")


class CapabilityAuthorityActivationAuthorizer:
    """Require a separate CK-NEXUS grant before non-read tools are model-visible.

    Connector reachability, installed permissions, admin rights, and schema discovery
    never constitute activation authority. The activation grant is consumed once and
    remains separate from the per-tool execution grant required for every invocation.
    """

    def __init__(
        self,
        authority: CapabilityAuthority,
        *,
        capability_mapper: ActivationCapabilityMapper = capability_id_for_write_activation,
    ) -> None:
        self.authority = authority
        self.capability_mapper = capability_mapper

    def authorize_activation(
        self,
        *,
        connector: ConnectorRecord,
        snapshot: DiscoverySnapshot,
        requested_state: ConnectorState,
        context: dict[str, Any],
    ) -> ConnectorActivationDecision:
        if requested_state is not ConnectorState.ACTIVE_WRITE:
            return ConnectorActivationDecision(False, "Only write activation is governed here.")

        identity = context.get("identity")
        if not isinstance(identity, CallerIdentity):
            return ConnectorActivationDecision(False, "Trusted caller identity is required.")
        if any(tool.risk is RiskClass.UNKNOWN for tool in snapshot.tools):
            return ConnectorActivationDecision(
                False,
                "Unknown-risk connector tools block write activation.",
            )
        has_verified_non_read = any(
            tool.risk in {RiskClass.WRITE, RiskClass.DESTRUCTIVE}
            for tool in snapshot.tools
        )
        if not has_verified_non_read:
            return ConnectorActivationDecision(
                False,
                "Connector has no verified non-read tools to activate.",
            )

        capability_id = self.capability_mapper(connector)
        params = write_activation_authority_params(connector, snapshot)
        try:
            decision = self.authority.enforce(
                identity,
                capability_id,
                params,
                _authority_context(context),
            )
        except PolicyDenied as exc:
            return ConnectorActivationDecision(False, f"Policy denied: {exc.code}.")
        except (KeyError, TypeError, ValueError):
            return ConnectorActivationDecision(False, "Policy authority rejected the request.")

        grant = decision.get("executionGrant")
        if not isinstance(grant, dict):
            return ConnectorActivationDecision(
                False,
                "Policy authority did not issue a valid activation grant.",
            )
        if not self.authority.consume_grant(identity, grant, params, expected_task_id=context.get("taskId")):
            return ConnectorActivationDecision(False, "Activation grant could not be consumed.")

        grant_id = grant.get("grant_id")
        approval_ref = str(grant_id) if isinstance(grant_id, str) and grant_id else None
        return ConnectorActivationDecision(
            True,
            "One-time write-activation grant consumed.",
            approval_ref=approval_ref,
        )
