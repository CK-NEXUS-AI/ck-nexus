"""Standard MCP stdio server for the CK-NEXUS clean-room device bridge.

The server is intentionally independent from the quarantined AnyClaw Android runtime. It exposes
only read-only, workspace-confined tools. The official MCP Python SDK owns protocol framing and
stdio transport.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from creator_app.device_bridge.policy import BridgeCapability, evaluate_bridge
from creator_app.device_bridge.safe_solver import SafeProblemSolver, SolverPolicyError

SERVER_NAME = "CK-NEXUS Clean-room Device Bridge"
SERVER_VERSION = "2.0"
TOOL_SPECS: tuple[tuple[str, str], ...] = (
    ("bridge_status", "Show fail-closed bridge and quarantine status without credentials."),
    ("workspace_list", "List bounded metadata inside the approved CK-NEXUS workspace."),
    ("workspace_read_text", "Read a bounded UTF-8 workspace file with secret redaction."),
    ("workspace_sha256", "Hash a bounded workspace file without returning its contents."),
    ("solve_data_json", "Analyze bounded JSON and return structure metadata only."),
    ("solve_code_review", "Review code deterministically without executing it."),
)
TOOL_NAMES = tuple(name for name, _description in TOOL_SPECS)


def _workspace_root() -> Path:
    configured = os.getenv("CKNEXUS_WORKSPACE_ROOT")
    root = Path(configured) if configured else Path.cwd()
    return root.expanduser().resolve(strict=True)


def _solver() -> SafeProblemSolver:
    return SafeProblemSolver(_workspace_root())


def _error(exc: Exception) -> dict[str, Any]:
    """Return a bounded policy error without host paths, tracebacks, or credential material."""
    if isinstance(exc, SolverPolicyError):
        reason = str(exc)[:120]
    else:
        reason = "tool_failed_closed"
    return {"ok": False, "error": reason}


def build_server() -> FastMCP:
    """Build the exact MCP tool registry used by the QR/descriptor generator."""
    server = FastMCP(SERVER_NAME, json_response=True)

    @server.tool()
    def bridge_status() -> dict[str, Any]:
        """Return the clean-room security posture; never call the quarantined Android package."""
        android = evaluate_bridge(
            package_id="gptos.intelligence.assistant",
            capability=BridgeCapability.READ_ONLY,
            exact_build_verified=False,
        )
        return {
            "ok": True,
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "transport": "stdio",
            "authority": "CK-NEXUS",
            "android_anyclaw_allowed": android.allowed,
            "android_anyclaw_reason": android.reason,
            "credential_access": False,
            "file_write": False,
            "system_exec": False,
            "production_mutation": False,
            "tool_names": list(TOOL_NAMES),
        }

    @server.tool()
    def workspace_list(path: str = ".") -> dict[str, Any]:
        """List bounded workspace metadata without following external paths."""
        try:
            return {"ok": True, **_solver().list_files(path)}
        except Exception as exc:  # policy boundary
            return _error(exc)

    @server.tool()
    def workspace_read_text(path: str) -> dict[str, Any]:
        """Read a bounded workspace text file after secret redaction."""
        try:
            return {"ok": True, **_solver().read_text(path)}
        except Exception as exc:  # policy boundary
            return _error(exc)

    @server.tool()
    def workspace_sha256(path: str) -> dict[str, Any]:
        """Return the SHA-256 of a bounded workspace file."""
        try:
            return {"ok": True, **_solver().sha256_file(path)}
        except Exception as exc:  # policy boundary
            return _error(exc)

    @server.tool()
    def solve_data_json(data: str) -> dict[str, Any]:
        """Analyze JSON without persisting or returning the raw input."""
        try:
            return {"ok": True, **_solver().analyze_json(data)}
        except Exception as exc:  # policy boundary
            return _error(exc)

    @server.tool()
    def solve_code_review(code: str) -> dict[str, Any]:
        """Review code for dangerous primitives without executing it."""
        try:
            return {"ok": True, **_solver().review_code(code)}
        except Exception as exc:  # policy boundary
            return _error(exc)

    return server


mcp = build_server()


if __name__ == "__main__":
    # No transport argument means stdio in the official MCP Python SDK.
    mcp.run()
