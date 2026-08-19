"""Fail-closed execution contracts for governed development assistants.

This module does not launch third-party software. It defines the envelope that
an independently controlled CK-NEXUS sandbox executor must satisfy before an
assistant may run. Provider CLIs remain workers, never authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .orchestrator import DevAssistantFabric
from .registry import AssistantStatus, get_assistant


class IsolationMode(StrEnum):
    """Supported isolation contracts for development work."""

    DISPOSABLE_WORKTREE = "disposable_worktree"
    DISPOSABLE_CONTAINER = "disposable_container"


class NetworkMode(StrEnum):
    """Network policy applied by the external sandbox executor."""

    DENY = "deny"
    BROKERED = "brokered"


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Policy requirements that a sandbox executor must enforce."""

    isolation: IsolationMode = IsolationMode.DISPOSABLE_WORKTREE
    network: NetworkMode = NetworkMode.DENY
    timeout_seconds: int = 900
    max_output_bytes: int = 1_000_000
    read_only_source: bool = True
    patch_only_output: bool = True
    external_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        if not 1 <= self.max_output_bytes <= 10_000_000:
            raise ValueError("max_output_bytes must be between 1 and 10000000")
        if self.external_mutation_authorized:
            raise ValueError("development assistant external mutation is fail-closed")


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Normalized task request passed into the execution contract."""

    assistant_id: str
    task: str
    workstream_id: str
    required_capabilities: tuple[str, ...] = ()
    credential_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.assistant_id.strip():
            raise ValueError("assistant_id must not be empty")
        if not self.task.strip():
            raise ValueError("task must not be empty")
        if not self.workstream_id.strip():
            raise ValueError("workstream_id must not be empty")
        for ref in self.credential_refs:
            if not ref.startswith("cred://"):
                raise ValueError("credential_refs must use opaque cred:// references")


class DevExecutionContract:
    """Build deterministic sandbox plans without executing provider software."""

    def __init__(self, fabric: DevAssistantFabric | None = None) -> None:
        self._fabric = fabric or DevAssistantFabric()

    def build_plan(
        self,
        request: ExecutionRequest,
        policy: ExecutionPolicy | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic, non-executing sandbox plan."""
        effective_policy = policy or ExecutionPolicy()
        spec = get_assistant(request.assistant_id)
        if spec.status is not AssistantStatus.ACTIVE:
            raise ValueError("assistant is not active for execution planning")

        required = frozenset(item.strip() for item in request.required_capabilities if item.strip())
        missing = required - spec.capabilities
        if missing:
            raise ValueError(f"assistant lacks required capabilities: {sorted(missing)}")

        discovered = {
            row["assistant_id"]: row
            for row in self._fabric.discover()
        }
        availability = discovered.get(spec.assistant_id, {})
        command = availability.get("command")

        request_digest = _digest_request(request)
        execution_id = f"devexec-{request_digest[:20]}"
        return {
            "execution_id": execution_id,
            "request_digest": request_digest,
            "assistant_id": spec.assistant_id,
            "assistant_name": spec.name,
            "command": command,
            "assistant_available": bool(availability.get("available")),
            "task_transport": "brokered_input",
            "credential_refs": list(request.credential_refs),
            "required_capabilities": sorted(required),
            "policy": {
                "isolation": effective_policy.isolation.value,
                "network": effective_policy.network.value,
                "timeout_seconds": effective_policy.timeout_seconds,
                "max_output_bytes": effective_policy.max_output_bytes,
                "read_only_source": effective_policy.read_only_source,
                "patch_only_output": effective_policy.patch_only_output,
                "external_mutation_authorized": False,
            },
            "executor": "cknexus_sandbox_executor",
            "execution_state": "PLANNED_NOT_EXECUTED",
            "release_evidence": False,
            "production_status": "NO-GO",
            "authority": "CK-NEXUS",
        }


def _digest_request(request: ExecutionRequest) -> str:
    payload = {
        "assistant_id": request.assistant_id.strip(),
        "task": request.task.strip(),
        "workstream_id": request.workstream_id.strip(),
        "required_capabilities": sorted(request.required_capabilities),
        "credential_refs": sorted(request.credential_refs),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
