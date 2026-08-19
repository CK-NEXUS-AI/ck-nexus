"""CK-NEXUS Universal development MCP server.

This module exposes a real Model Context Protocol Streamable HTTP endpoint at
``/mcp``. It is intentionally Post-P0/development-only and binds to loopback;
a remote ChatGPT connection must be provided by a separately authenticated
HTTPS/Secure MCP boundary rather than exposing this port directly.

Run locally::

    python -m creator_app.agnes.mcp_server

Defaults:
- host: 127.0.0.1
- port: 8765
- MCP endpoint: http://127.0.0.1:8765/mcp
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from creator_app.ai_team.universal_system import UniversalSystem
from creator_app.core.self_capability_manager import (
    CORE_CAPABILITIES,
    LEARNING_SOURCES,
    SelfCapabilityManager,
)
from creator_app.dev_assistants import (
    DevAssistantFabric,
    DevExecutionContract,
    ExecutionPolicy,
    ExecutionRequest,
)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_DEFAULT_PORT = 8765


def _configured_host() -> str:
    host = os.getenv("CKNEXUS_UNIVERSAL_MCP_HOST", "127.0.0.1").strip().lower()
    if host not in _LOOPBACK_HOSTS:
        raise RuntimeError(
            "CK-NEXUS Universal MCP is loopback-only. "
            "Use an authenticated HTTPS/Secure MCP boundary for remote access."
        )
    return host


def _configured_port() -> int:
    raw = os.getenv("CKNEXUS_UNIVERSAL_MCP_PORT", str(_DEFAULT_PORT)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError("CKNEXUS_UNIVERSAL_MCP_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("CKNEXUS_UNIVERSAL_MCP_PORT must be between 1 and 65535")
    return port


_SYSTEM: UniversalSystem | None = None
_CAPABILITY_MANAGER: SelfCapabilityManager | None = None
_DEV_ASSISTANT_FABRIC: DevAssistantFabric | None = None
_DEV_EXECUTION_CONTRACT: DevExecutionContract | None = None


def get_system() -> UniversalSystem:
    """Return the lazily-created Universal System development runtime."""
    global _SYSTEM
    if _SYSTEM is None:
        _SYSTEM = UniversalSystem()
    return _SYSTEM


def get_capability_manager() -> SelfCapabilityManager:
    """Return the lazily-created self-capability inventory."""
    global _CAPABILITY_MANAGER
    if _CAPABILITY_MANAGER is None:
        _CAPABILITY_MANAGER = SelfCapabilityManager()
    return _CAPABILITY_MANAGER


def get_dev_assistant_fabric() -> DevAssistantFabric:
    """Return the fail-closed development-assistant discovery fabric."""
    global _DEV_ASSISTANT_FABRIC
    if _DEV_ASSISTANT_FABRIC is None:
        _DEV_ASSISTANT_FABRIC = DevAssistantFabric()
    return _DEV_ASSISTANT_FABRIC


def get_dev_execution_contract() -> DevExecutionContract:
    """Return the non-executing CK-NEXUS development execution contract."""
    global _DEV_EXECUTION_CONTRACT
    if _DEV_EXECUTION_CONTRACT is None:
        _DEV_EXECUTION_CONTRACT = DevExecutionContract(get_dev_assistant_fabric())
    return _DEV_EXECUTION_CONTRACT


mcp = FastMCP(
    "CK-NEXUS Universal Development",
    instructions=(
        "Post-P0 development tools only. CK-NEXUS remains authority. "
        "Results do not promote Q10/Q11/Q12, do not constitute release evidence, "
        "and do not authorize production mutation or merging PR #14."
    ),
    host=_configured_host(),
    port=_configured_port(),
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def cknexus_status() -> dict[str, Any]:
    """Return a redacted development status snapshot for the Universal System."""
    return {
        "status": "development",
        "production_status": "NO-GO",
        "authority": "CK-NEXUS",
        "runtime": get_system().status(),
        "release_evidence": False,
    }


@mcp.tool()
def cknexus_capabilities() -> dict[str, Any]:
    """List declared capabilities without exposing credentials or local secrets."""
    manager = get_capability_manager()
    return {
        "production_status": "NO-GO",
        "release_evidence": False,
        "universal": get_system().list_capabilities(),
        "declared_self_capabilities": CORE_CAPABILITIES,
        "limitations": manager.get_limitations_and_workarounds()["cannot_do"],
    }


@mcp.tool()
def cknexus_team() -> dict[str, Any]:
    """Return the seven-role AI-team development registry and current status."""
    system = get_system()
    return {
        "production_status": "NO-GO",
        "release_evidence": False,
        "team": system.team.list_team(),
        "status": system.team.team_status(),
    }


@mcp.tool()
def cknexus_plan(request: str, priority: int = 2) -> dict[str, Any]:
    """Run the Universal System planning/simulation path for a development request.

    This tool does not grant external mutation authority. Provider/tool execution
    still requires the independent CK-NEXUS policy, credential, and approval path.
    """
    request = request.strip()
    if not request:
        raise ValueError("request must not be empty")
    if priority not in {1, 2, 3}:
        raise ValueError("priority must be 1, 2, or 3")
    result = get_system().process(request, priority=priority)
    return {
        "status": "planned",
        "result": result,
        "production_status": "NO-GO",
        "release_evidence": False,
        "external_mutation_authorized": False,
    }


@mcp.tool()
def cknexus_discovery_catalog() -> dict[str, Any]:
    """Return configured learning-source metadata without performing network discovery."""
    return {
        "status": "catalog-only",
        "sources": LEARNING_SOURCES,
        "network_scan_executed": False,
        "production_status": "NO-GO",
        "release_evidence": False,
    }


@mcp.tool()
def cknexus_dev_assistants() -> dict[str, Any]:
    """Discover approved local developer assistants without installing or executing them."""
    fabric = get_dev_assistant_fabric()
    return {
        "status": "discovery-only",
        "authority": "CK-NEXUS",
        "production_status": "NO-GO",
        "release_evidence": False,
        "external_mutation_authorized": False,
        "assistants": fabric.discover(),
    }


@mcp.tool()
def cknexus_dev_execution_plan(
    assistant_id: str,
    task: str,
    workstream_id: str = "default",
) -> dict[str, Any]:
    """Build a fail-closed sandbox execution plan without launching the assistant."""
    request = ExecutionRequest(
        assistant_id=assistant_id,
        task=task,
        workstream_id=workstream_id,
    )
    return get_dev_execution_contract().build_plan(request, ExecutionPolicy())


def run_server() -> None:
    """Run the loopback Streamable HTTP MCP server until interrupted."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run_server()
