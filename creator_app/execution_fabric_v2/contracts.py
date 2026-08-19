"""Capability leases and bounded execution contracts for CK-NEXUS Execution Fabric V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ExecutionAction(StrEnum):
    READ = "read"
    ANALYZE = "analyze"
    PATCH_CREATE = "patch_create"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    PRODUCTION_MUTATION = "production_mutation"


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    timeout_seconds: int = 300
    memory_bytes: int = 1_073_741_824
    cpus: float = 1.0
    pids_limit: int = 128
    output_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        if not 134_217_728 <= self.memory_bytes <= 8_589_934_592:
            raise ValueError("memory_bytes must be between 128 MiB and 8 GiB")
        if not 0.1 <= self.cpus <= 8.0:
            raise ValueError("cpus must be between 0.1 and 8.0")
        if not 16 <= self.pids_limit <= 512:
            raise ValueError("pids_limit must be between 16 and 512")
        if not 1024 <= self.output_bytes <= 16_777_216:
            raise ValueError("output_bytes must be between 1 KiB and 16 MiB")


@dataclass(frozen=True, slots=True)
class CapabilityLease:
    lease_id: str
    capability: str
    scope: str
    expires_at: datetime
    max_actions: int = 1
    network_domains: frozenset[str] = field(default_factory=frozenset)
    credential_refs: tuple[str, ...] = ()
    approved_by: str = "policy"
    release_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.lease_id.startswith("lease-"):
            raise ValueError("lease_id must start with lease-")
        if not self.capability.strip() or not self.scope.strip():
            raise ValueError("capability and scope must not be empty")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if not 1 <= self.max_actions <= 100:
            raise ValueError("max_actions must be between 1 and 100")
        if "*" in self.network_domains:
            raise ValueError("wildcard network access is forbidden")
        if any(not ref.startswith("cred://") for ref in self.credential_refs):
            raise ValueError("credential_refs must be opaque cred:// references")

    @property
    def active(self) -> bool:
        return datetime.now(UTC) < self.expires_at


@dataclass(frozen=True, slots=True)
class ExecutionProposal:
    action: ExecutionAction
    capability: str
    scope: str
    destination_domain: str | None = None
    user_approved: bool = False
    patch_only: bool = True
    budget: ResourceBudget = ResourceBudget()


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    allowed: bool
    reason: str
    lease_id: str
    capability: str
    scope: str
    network_allowed: bool
    credential_refs: tuple[str, ...]
    patch_only: bool
    authority: str = "CK-NEXUS"
