"""Validate local MCP connection descriptors before a device bridge is trusted."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_ALLOWED_INTERPRETERS = {"python", "python3"}
_ALLOWED_MODULES = {"creator_app.device_bridge.mcp_server_v2"}
_FORBIDDEN_SHELL_CHARS = {";", "|", "&", "`", "\n", "\r", ">", "<"}


class DescriptorError(ValueError):
    """Raised when a connection descriptor fails validation."""


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str


@dataclass(frozen=True)
class ConnectionDescriptor:
    name: str
    version: str
    tools: tuple[ToolDescriptor, ...]
    method: str
    command: tuple[str, ...]
    cwd: str


def _require_text(value: Any, field: str, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise DescriptorError(f"{field}_must_be_string")
    text = value.strip()
    if not text or len(text) > max_len:
        raise DescriptorError(f"{field}_invalid_length")
    if "\x00" in text:
        raise DescriptorError(f"{field}_contains_nul")
    return text


def _parse_tools(raw_tools: Any) -> tuple[ToolDescriptor, ...]:
    if not isinstance(raw_tools, list) or not raw_tools or len(raw_tools) > 64:
        raise DescriptorError("tools_invalid")

    result: list[ToolDescriptor] = []
    seen: set[str] = set()
    for item in raw_tools:
        if not isinstance(item, dict):
            raise DescriptorError("tool_must_be_object")
        name = _require_text(item.get("name"), "tool_name", max_len=64)
        if not _TOOL_NAME_RE.fullmatch(name):
            raise DescriptorError("tool_name_invalid")
        if name in seen:
            raise DescriptorError("duplicate_tool_name")
        description = _require_text(
            item.get("description"),
            "tool_description",
            max_len=500,
        )
        result.append(ToolDescriptor(name=name, description=description))
        seen.add(name)
    return tuple(result)


def _parse_command(command_text: Any) -> tuple[str, ...]:
    command = _require_text(command_text, "command", max_len=500)
    if any(char in command for char in _FORBIDDEN_SHELL_CHARS):
        raise DescriptorError("command_contains_shell_metacharacter")

    try:
        argv = tuple(shlex.split(command, posix=True))
    except ValueError as exc:
        raise DescriptorError("command_invalid_quoting") from exc

    if not argv or argv[0] not in _ALLOWED_INTERPRETERS:
        raise DescriptorError("command_not_allowlisted")

    if len(argv) == 3 and argv[1] == "-m":
        if argv[2] not in _ALLOWED_MODULES:
            raise DescriptorError("module_not_allowlisted")
        return argv

    if len(argv) != 2:
        raise DescriptorError("command_not_allowlisted")

    script = PurePosixPath(argv[1])
    if script.is_absolute() or ".." in script.parts:
        raise DescriptorError("script_path_outside_workspace")
    if script.suffix != ".py" or script.parts[:1] != ("creator_app",):
        raise DescriptorError("script_path_not_allowlisted")
    return argv


def parse_descriptor(payload: str) -> ConnectionDescriptor:
    """Parse and validate a connection descriptor from QR or other untrusted input."""
    if len(payload.encode("utf-8")) > 16_384:
        raise DescriptorError("descriptor_too_large")

    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DescriptorError("descriptor_invalid_json") from exc
    if not isinstance(raw, dict):
        raise DescriptorError("descriptor_must_be_object")

    name = _require_text(raw.get("name"), "name", max_len=100)
    version = _require_text(raw.get("version"), "version", max_len=40)
    tools = _parse_tools(raw.get("tools"))

    connection = raw.get("connection")
    if not isinstance(connection, dict):
        raise DescriptorError("connection_must_be_object")
    method = _require_text(connection.get("method"), "method", max_len=20)
    if method != "stdio":
        raise DescriptorError("unsupported_connection_method")

    command = _parse_command(connection.get("command"))
    cwd = _require_text(connection.get("cwd"), "cwd", max_len=500)
    posix_cwd = PurePosixPath(cwd)
    windows_cwd = PureWindowsPath(cwd)
    is_absolute = posix_cwd.is_absolute() or windows_cwd.is_absolute()
    has_parent = ".." in posix_cwd.parts or ".." in windows_cwd.parts
    if not is_absolute or has_parent:
        raise DescriptorError("cwd_must_be_absolute_clean_path")

    return ConnectionDescriptor(
        name=name,
        version=version,
        tools=tools,
        method=method,
        command=command,
        cwd=cwd,
    )


def validate_registry_match(
    descriptor: ConnectionDescriptor,
    runtime_tools: Iterable[str],
) -> None:
    """Require the QR-advertised tool set to equal the exact runtime registry."""
    advertised = {tool.name for tool in descriptor.tools}
    runtime = set(runtime_tools)
    if advertised != runtime:
        missing = sorted(advertised - runtime)
        unexpected = sorted(runtime - advertised)
        raise DescriptorError(
            "registry_mismatch:"
            f"missing_runtime={','.join(missing) or '-'};"
            f"unexpected_runtime={','.join(unexpected) or '-'}"
        )


def connection_fingerprint(descriptor: ConnectionDescriptor) -> str:
    """Return a stable SHA-256 fingerprint for evidence and QR drift detection."""
    canonical = {
        "name": descriptor.name,
        "version": descriptor.version,
        "tools": [
            {"name": tool.name, "description": tool.description}
            for tool in descriptor.tools
        ],
        "connection": {
            "method": descriptor.method,
            "command": list(descriptor.command),
            "cwd": descriptor.cwd,
        },
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
