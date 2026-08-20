"""Standard MCP server for the CK-NEXUS clean-room device bridge.

The server is intentionally independent from the quarantined AnyClaw Android runtime. It exposes
only read-only, workspace-confined tools. Local use defaults to stdio; authenticated remote use may
inject MCP authorization settings and a token verifier without changing the tool registry.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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
_TOOL_DESCRIPTIONS = dict(TOOL_SPECS)
_READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _workspace_root() -> Path:
    configured = os.getenv("CKNEXUS_WORKSPACE_ROOT")
    root = Path(configured) if configured else Path.cwd()
    return root.expanduser().resolve(strict=True)


def _solver() -> SafeProblemSolver:
    return SafeProblemSolver(_workspace_root())


def _error(exc: Exception) -> dict[str, Any]:
    """Return a bounded policy error without host paths, tracebacks, or credential material."""
    reason = str(exc)[:120] if isinstance(exc, SolverPolicyError) else "tool_failed_closed"
    return {"ok": False, "error": reason}


def build_server(
    *,
    auth: AuthSettings | None = None,
    token_verifier: TokenVerifier | None = None,
    transport_label: str = "stdio",
    host: str | None = None,
    port: int | None = None,
    stateless_http: bool | None = None,
    max_request_body_size: int | None = None,
) -> FastMCP:
    """Build the exact clean-room tool registry with optional HTTP authorization.

    Local stdio keeps HTTP settings unset. A remote Streamable HTTP server must inject
    authorization, remain loopback-bound, use stateless requests, and bound request bodies.
    """
    if (auth is None) != (token_verifier is None):
        raise ValueError("auth_and_token_verifier_must_be_paired")
    if transport_label not in {"stdio", "streamable-http"}:
        raise ValueError("unsupported_transport_label")
    if transport_label == "streamable-http" and (auth is None or token_verifier is None):
        raise ValueError("remote_transport_requires_auth")

    kwargs: dict[str, Any] = {"json_response": True}
    if auth is not None and token_verifier is not None:
        kwargs.update({"auth": auth, "token_verifier": token_verifier})
    if host is not None:
        kwargs["host"] = host
    if port is not None:
        kwargs["port"] = port
    if stateless_http is not None:
        kwargs["stateless_http"] = stateless_http
    if max_request_body_size is not None:
        if max_request_body_size <= 0:
            raise ValueError("max_request_body_size_must_be_positive")
        kwargs["max_request_body_size"] = max_request_body_size
    server = FastMCP(SERVER_NAME, **kwargs)

    @server.tool(
        description=_TOOL_DESCRIPTIONS["bridge_status"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
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
            "transport": transport_label,
            "authority": "CK-NEXUS",
            "android_anyclaw_allowed": android.allowed,
            "android_anyclaw_reason": android.reason,
            "credential_access": False,
            "file_write": False,
            "system_exec": False,
            "production_mutation": False,
            "tool_names": list(TOOL_NAMES),
        }

    @server.tool(
        description=_TOOL_DESCRIPTIONS["workspace_list"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def workspace_list(path: str = ".") -> dict[str, Any]:
        try:
            return {"ok": True, **_solver().list_files(path)}
        except Exception as exc:
            return _error(exc)

    @server.tool(
        description=_TOOL_DESCRIPTIONS["workspace_read_text"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def workspace_read_text(path: str) -> dict[str, Any]:
        try:
            return {"ok": True, **_solver().read_text(path)}
        except Exception as exc:
            return _error(exc)

    @server.tool(
        description=_TOOL_DESCRIPTIONS["workspace_sha256"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def workspace_sha256(path: str) -> dict[str, Any]:
        try:
            return {"ok": True, **_solver().sha256_file(path)}
        except Exception as exc:
            return _error(exc)

    @server.tool(
        description=_TOOL_DESCRIPTIONS["solve_data_json"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def solve_data_json(data: str) -> dict[str, Any]:
        try:
            return {"ok": True, **_solver().analyze_json(data)}
        except Exception as exc:
            return _error(exc)

    @server.tool(
        description=_TOOL_DESCRIPTIONS["solve_code_review"],
        annotations=_READ_ONLY_ANNOTATIONS,
    )
    def solve_code_review(code: str) -> dict[str, Any]:
        try:
            return {"ok": True, **_solver().review_code(code)}
        except Exception as exc:
            return _error(exc)

    return server


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
