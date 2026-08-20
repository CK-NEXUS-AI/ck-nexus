"""Measure local checkout and MCP registry before emitting device-bridge metadata.

All subprocess calls are fixed local argv calls. No shell or network command is accepted from a
caller. A dirty checkout, registry drift, protocol failure, or missing source identity fails closed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from creator_app.device_bridge import parse_descriptor, validate_registry_match
from creator_app.device_bridge.descriptor_generator import build_descriptor, descriptor_sha256
from creator_app.device_bridge.mcp_server_v2 import TOOL_SPECS

_GIT_TIMEOUT_SECONDS = 5
_MCP_TIMEOUT_SECONDS = 10


class AttestationError(RuntimeError):
    """Raised when local source/runtime attestation cannot be proven."""


@dataclass(frozen=True)
class CheckoutAttestation:
    """Exact local source identity required for descriptor generation."""

    commit_sha: str
    tree_sha: str
    clean: bool


def _run_git(root: Path, *args: str) -> str:
    """Run one fixed local git command without a shell or caller-controlled executable."""
    completed = subprocess.run(  # noqa: S603 - fixed executable and bounded internal argv only
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if completed.returncode != 0:
        raise AttestationError("git_measurement_failed")
    return completed.stdout.strip()


def measure_checkout(workspace_root: str | Path) -> CheckoutAttestation:
    """Require a clean Git worktree and return exact commit/tree identities."""
    root = Path(workspace_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise AttestationError("workspace_root_not_directory")
    if _run_git(root, "rev-parse", "--is-inside-work-tree") != "true":
        raise AttestationError("not_git_worktree")

    commit = _run_git(root, "rev-parse", "HEAD").lower()
    tree = _run_git(root, "rev-parse", "HEAD^{tree}").lower()
    dirty = _run_git(root, "status", "--porcelain=v1", "--untracked-files=normal")

    if not _is_sha1(commit) or not _is_sha1(tree):
        raise AttestationError("invalid_git_identity")
    if dirty:
        raise AttestationError("dirty_checkout_denied")
    return CheckoutAttestation(commit_sha=commit, tree_sha=tree, clean=True)


def _is_sha1(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _runtime_registry_digest(tools: list[dict[str, str]]) -> str:
    encoded = json.dumps(
        tools,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def probe_runtime_registry(workspace_root: str | Path) -> list[dict[str, str]]:
    """Launch the CK-owned MCP server over stdio and read its actual protocol tool registry."""
    root = Path(workspace_root).expanduser().resolve(strict=True)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "creator_app.device_bridge.mcp_server_v2"],
        env={
            "CKNEXUS_WORKSPACE_ROOT": str(root),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        },
    )
    try:
        async with (
            stdio_client(params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await asyncio.wait_for(session.initialize(), timeout=_MCP_TIMEOUT_SECONDS)
            result = await asyncio.wait_for(session.list_tools(), timeout=_MCP_TIMEOUT_SECONDS)
    except (OSError, RuntimeError, TimeoutError) as exc:
        raise AttestationError("mcp_registry_probe_failed") from exc

    return [
        {"name": tool.name, "description": tool.description or ""}
        for tool in result.tools
    ]


async def build_attested_descriptor(workspace_root: str | Path) -> dict[str, Any]:
    """Build descriptor only after exact source and live MCP registry measurements agree."""
    checkout = measure_checkout(workspace_root)
    runtime_tools = await probe_runtime_registry(workspace_root)
    expected_tools = [
        {"name": name, "description": description}
        for name, description in TOOL_SPECS
    ]
    if runtime_tools != expected_tools:
        raise AttestationError("runtime_registry_drift")

    descriptor = build_descriptor(
        workspace_root=workspace_root,
        source_commit=checkout.commit_sha,
    )
    parsed = parse_descriptor(json.dumps(descriptor, ensure_ascii=False))
    validate_registry_match(parsed, [tool["name"] for tool in runtime_tools])

    descriptor["integrity"].update(
        {
            "source_tree": checkout.tree_sha,
            "checkout_clean": checkout.clean,
            "runtime_registry_sha256": _runtime_registry_digest(runtime_tools),
        }
    )
    descriptor["integrity"]["descriptor_sha256"] = descriptor_sha256(descriptor)
    return descriptor
