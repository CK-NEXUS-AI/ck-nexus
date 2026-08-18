from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NetworkPolicy = Literal["deny_all", "allowlisted"]


class ResourceLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_ms: int = Field(gt=0)
    memory_mb: int = Field(gt=0)
    cpu_ms: int = Field(gt=0)
    pids_max: int = Field(gt=0)
    output_bytes_max: int = Field(gt=0)


class FilesystemPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root: Literal["read_only"] = "read_only"
    work: Literal["tmpfs"] = "tmpfs"
    output: Literal["copy_out"] = "copy_out"


class SecurityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user: str = "nobody"
    cap_drop: tuple[str, ...] = ("ALL",)
    no_new_privileges: bool = True
    seccomp: Literal["default", "custom"] = "default"
    read_only_root: bool = True


class ExecutionSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    spec_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    runtime_version: str = Field(min_length=1)
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    command: tuple[str, ...] = Field(min_length=1)
    limits: ResourceLimits
    network_policy: NetworkPolicy = "deny_all"
    filesystem_policy: FilesystemPolicy = FilesystemPolicy()
    security: SecurityPolicy = SecurityPolicy()
    approval_ref: str | None = None
    policy_decision_id: str | None = None


ExecutionStatus = Literal[
    "success",
    "compile_error",
    "runtime_error",
    "timeout",
    "oom",
    "output_limit",
    "policy_denied",
    "infrastructure_error",
]


class ExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ExecutionStatus
    exit_code: int | None = None
    signal: int | None = None
    stdout: str = ""
    stderr: str = ""
    stdout_bytes: int = Field(default=0, ge=0)
    stderr_bytes: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    memory_peak_bytes: int = Field(default=0, ge=0)
    cpu_usage_us: int = Field(default=0, ge=0)
    artifact_refs: tuple[dict[str, str], ...] = ()
    cleanup_status: Literal["success", "failed", "unknown"] = "unknown"
    runner_version: str = Field(min_length=1)
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_decision_id: str | None = None
    evidence_hash: str | None = None
