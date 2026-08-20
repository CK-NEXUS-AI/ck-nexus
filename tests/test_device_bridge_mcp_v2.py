from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from creator_app.device_bridge import parse_descriptor, validate_registry_match
from creator_app.device_bridge.descriptor_generator import (
    build_descriptor,
    descriptor_sha256,
    encode_descriptor,
    registry_sha256,
)
from creator_app.device_bridge.mcp_server_v2 import TOOL_NAMES, TOOL_SPECS


def test_generated_descriptor_matches_exact_runtime_registry(tmp_path: Path) -> None:
    script = tmp_path / "creator_app" / "device_bridge" / "mcp_server_v2.py"
    script.parent.mkdir(parents=True)
    script.write_text("# test fixture\n", encoding="utf-8")

    descriptor = build_descriptor(workspace_root=tmp_path, source_commit="a" * 40)
    payload = encode_descriptor(descriptor)
    parsed = parse_descriptor(payload)

    validate_registry_match(parsed, TOOL_NAMES)
    assert parsed.command == ("python3", "-m", "creator_app.device_bridge.mcp_server_v2")
    assert descriptor["integrity"]["registry_sha256"] == registry_sha256()
    assert len(descriptor_sha256(descriptor)) == 64
    assert [tool["name"] for tool in descriptor["tools"]] == list(TOOL_NAMES)


def test_registry_excludes_unsafe_legacy_problem_solver_tools() -> None:
    names = set(TOOL_NAMES)

    assert "solve_system" not in names
    assert "solve_web" not in names
    assert "solve_file" not in names
    assert "anyclaw_failover" not in names
    assert all(name for name, _description in TOOL_SPECS)


@pytest.mark.asyncio
async def test_standard_mcp_stdio_lists_exact_tools() -> None:
    repo_root = Path.cwd().resolve()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "creator_app.device_bridge.mcp_server_v2"],
        env={"CKNEXUS_WORKSPACE_ROOT": str(repo_root)},
    )

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=10)
        result = await asyncio.wait_for(session.list_tools(), timeout=10)

    assert {tool.name for tool in result.tools} == set(TOOL_NAMES)
