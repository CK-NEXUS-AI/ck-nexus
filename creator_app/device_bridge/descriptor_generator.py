"""Generate connection descriptors from the exact clean-room MCP registry.

The descriptor is metadata only. It does not grant trust to a device package or bypass the bridge
policy. A QR renderer may encode the returned JSON after independent runtime verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from creator_app.device_bridge.mcp_server_v2 import SERVER_NAME, SERVER_VERSION, TOOL_SPECS

_SERVER_SCRIPT = "creator_app/device_bridge/mcp_server_v2.py"
_SERVER_MODULE = "creator_app.device_bridge.mcp_server_v2"


def registry_sha256() -> str:
    """Digest the exact advertised tool registry in a stable representation."""
    encoded = json.dumps(
        [{"name": name, "description": description} for name, description in TOOL_SPECS],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_descriptor(
    *,
    workspace_root: str | Path,
    source_commit: str,
) -> dict[str, Any]:
    """Build a stdio descriptor from the exact V2 tool registry."""
    root = Path(workspace_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root_not_directory")

    commit = source_commit.strip().lower()
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("source_commit_must_be_full_sha1")

    script = root / _SERVER_SCRIPT
    if not script.is_file():
        raise ValueError("mcp_server_script_missing")

    return {
        "schema": "ck-nexus-device-bridge/v2",
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "tools": [
            {"name": name, "description": description}
            for name, description in TOOL_SPECS
        ],
        "connection": {
            "method": "stdio",
            "command": f"python3 -m {_SERVER_MODULE}",
            "cwd": str(root),
        },
        "integrity": {
            "source_commit": commit,
            "registry_sha256": registry_sha256(),
        },
        "security": {
            "authority": "CK-NEXUS",
            "read_only": True,
            "credential_access": False,
            "system_exec": False,
            "file_write": False,
            "production_mutation": False,
            "android_package_trust": "separate_gate",
        },
    }


def encode_descriptor(descriptor: dict[str, Any]) -> str:
    """Return canonical UTF-8 JSON suitable for QR encoding."""
    return json.dumps(
        descriptor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def descriptor_sha256(descriptor: dict[str, Any]) -> str:
    """Digest the canonical QR payload for evidence/drift detection."""
    return hashlib.sha256(encode_descriptor(descriptor).encode("utf-8")).hexdigest()
