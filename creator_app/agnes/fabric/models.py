"""Core contracts for the AGNES capability fabric.

The fabric is intentionally dependency-light. External engines are described as
optional capabilities and are never imported merely because they are catalogued.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class ModuleKind(StrEnum):
    COGNITIVE = "COGNITIVE"
    RESEARCH = "RESEARCH"
    PROTOCOL = "PROTOCOL"
    WORKFLOW = "WORKFLOW"
    IDENTITY = "IDENTITY"
    SECURITY = "SECURITY"
    DOCUMENT = "DOCUMENT"
    DATA = "DATA"
    MEMORY = "MEMORY"
    RESOURCE = "RESOURCE"
    QUALITY = "QUALITY"
    MULTIMODAL = "MULTIMODAL"
    ASSET = "ASSET"
    EDGE = "EDGE"
    OBSERVABILITY = "OBSERVABILITY"
    EVALUATION = "EVALUATION"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    ECONOMICS = "ECONOMICS"
    PRIVACY = "PRIVACY"
    EVIDENCE = "EVIDENCE"
    SELF_IMPROVEMENT = "SELF_IMPROVEMENT"


class RiskClass(StrEnum):
    R0_READ = "R0_READ"
    R1_TEMPORARY = "R1_TEMPORARY"
    R2_REVERSIBLE_WRITE = "R2_REVERSIBLE_WRITE"
    R3_EXTERNAL_WRITE = "R3_EXTERNAL_WRITE"
    R4_CRITICAL = "R4_CRITICAL"


class ActivationMode(StrEnum):
    DISABLED = "DISABLED"
    READ_ONLY = "READ_ONLY"
    BOUNDED_WRITE = "BOUNDED_WRITE"


class ModuleStage(StrEnum):
    DISCOVERED = "DISCOVERED"
    INSPECTED = "INSPECTED"
    SCANNED = "SCANNED"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    ENABLED_READONLY = "ENABLED_READONLY"
    APPROVED_READWRITE = "APPROVED_READWRITE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class CapabilityModule:
    module_id: str
    name: str
    kind: ModuleKind
    description: str
    risk: RiskClass = RiskClass.R0_READ
    default_mode: ActivationMode = ActivationMode.READ_ONLY
    network_required: bool = False
    write_capable: bool = False
    optional_packages: tuple[str, ...] = ()
    optional_binaries: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ("linux", "android", "vps", "container")
    depends_on: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class DependencyStatus:
    package: str | None = None
    binary: str | None = None
    available: bool = False


@dataclass(frozen=True)
class ModuleProbe:
    module_id: str
    packages: tuple[DependencyStatus, ...] = ()
    binaries: tuple[DependencyStatus, ...] = ()

    @property
    def external_dependencies_ready(self) -> bool:
        statuses: Iterable[DependencyStatus] = (*self.packages, *self.binaries)
        return all(item.available for item in statuses)


@dataclass(frozen=True)
class ResourceSnapshot:
    total_ram_bytes: int | None
    available_ram_bytes: int | None
    load_1m: float | None
    memory_psi_avg10: float | None
    cpu_psi_avg10: float | None
    io_psi_avg10: float | None
    thermal_celsius: float | None
    zram_present: bool
    writable_cgroup_v2: bool
    cgroup_v2_present: bool = False


@dataclass(frozen=True)
class RuntimeDecision:
    quality_profile: str
    memory_tier: str
    max_concurrency: int
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
