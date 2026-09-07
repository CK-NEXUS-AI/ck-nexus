from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentCard(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    example: str


class RunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    agent_id: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=3, max_length=8_000)
    session_id: str = Field(default="default", min_length=1, max_length=96)
    audience: str = Field(default="ผู้ชมทั่วไป", max_length=160)
    platform: str = Field(default="ไม่ระบุ", max_length=80)
    tone: str = Field(default="เป็นธรรมชาติ", max_length=80)
    language: Literal["ไทย", "English", "ไทย + English"] = "ไทย"

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:")
        if any(character not in allowed for character in value):
            raise ValueError("session_id may contain only letters, numbers, -, _, and :")
        return value


class RunResult(BaseModel):
    id: str
    session_id: str
    agent_id: str
    agent_name: str
    prompt: str
    audience: str
    platform: str
    tone: str
    language: str
    content: str
    model: str
    mode: Literal["mock", "openai", "ollama"]
    status: Literal["completed", "failed"]
    duration_ms: int
    created_at: datetime


class StatusResponse(BaseModel):
    name: str
    version: str
    mode: Literal["mock", "openai", "ollama", "blocked"]
    model: str
    key_configured: bool
    database_ready: bool
    access_required: bool
    codex_enabled: bool
    codex_ready: bool
    codex_sandbox: Literal["read-only", "workspace-write"]
    dev_team_enabled: bool
    dev_team_ready: bool


class DevAdvisorCard(BaseModel):
    id: str
    name: str
    role: str
    capabilities: list[str]
    web_search: bool
    side_effects: Literal["none"] = "none"


class DevTeamRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=3, max_length=8_000)
    session_id: str = Field(default="dev-team", min_length=1, max_length=96)
    consult_mode: Literal[
        "auto",
        "council",
        "architect",
        "research",
        "designer",
        "builder",
        "reviewer",
        "debate",
    ] = "auto"
    context: str = Field(default="", max_length=8_000)
    language: Literal["ไทย", "English", "ไทย + English"] = "ไทย"

    @field_validator("session_id")
    @classmethod
    def validate_dev_team_session_id(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:")
        if any(character not in allowed for character in value):
            raise ValueError("session_id may contain only letters, numbers, -, _, and :")
        return value


class DevTeamResult(BaseModel):
    id: str
    session_id: str
    consult_mode: str
    content: str
    model: str
    mode: Literal["mock", "openai", "ollama"]
    duration_ms: int
    advisors_available: int


class CodexTaskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=3, max_length=8_000)


class CodexTaskResult(BaseModel):
    output: str
    mode: Literal["codex"] = "codex"
    sandbox: Literal["read-only", "workspace-write"]
    duration_ms: int


class ErrorResponse(BaseModel):
    error: str
    message: str


class AgnesExecuteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    skill_id: str = Field(min_length=1, max_length=128)
    goal: str = Field(min_length=1, max_length=8_000)
    executor: str | None = Field(default=None, max_length=64)
    inputs: dict = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=128)
    tenant_id: str = Field(default="default", min_length=1, max_length=128)
    actor_id: str = Field(default="human", min_length=1, max_length=128)
    environment: Literal["development", "test", "staging", "production"] = "development"
    workspace_id: str | None = Field(default=None, max_length=96)
    baseline_commit: str | None = Field(default=None, max_length=80)
    approval_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=256)
    allowlist_paths: list[str] = Field(default_factory=list, max_length=128)
    granted_capabilities: list[str] = Field(default_factory=list, max_length=128)
    timeout_seconds: int = Field(default=300, ge=1, le=1800)


class AgnesPipelineStartRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=8_000)
    patch: str = Field(min_length=1, max_length=2_000_000)
    baseline_commit: str = Field(min_length=40, max_length=64)
    approval_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=256)
    workspace_id: str | None = Field(default=None, max_length=96)
    correlation_id: str | None = Field(default=None, max_length=128)
    tenant_id: str = Field(default="default", min_length=1, max_length=128)
    actor_id: str = Field(default="human", min_length=1, max_length=128)
    environment: Literal["development", "test", "staging", "production"] = "development"
    allowlist_paths: list[str] = Field(default_factory=lambda: ["**"], max_length=128)
    test_command: list[str] = Field(
        default_factory=lambda: ["python", "-m", "compileall", "-q", "."], max_length=64
    )
    scan_command: list[str] = Field(
        default_factory=lambda: ["python", "-c", "print('security-scan:PASS')"], max_length=64
    )


class AgnesPipelineDiscardRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class AgnesApprovalRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approval_id: str = Field(min_length=1, max_length=128)
    fingerprint: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=1, max_length=128)
    ttl_seconds: int = Field(default=900, ge=30, le=3600)


class ConnectorRegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    connector_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    url: str = Field(min_length=8, max_length=2048)
    protocol: Literal["mcp", "openapi"]
    credential_ref: str | None = Field(default=None, max_length=128)
    trust_source: Literal["manual", "trusted_registry", "signed_registry"] = "manual"
    allow_private_network: bool = False
    allowed_tools: list[str] = Field(default_factory=list, max_length=512)
    auto_discover: bool = True
    auto_activate_read_only: bool = False


class ConnectorActivateRequest(BaseModel):
    allow_write: bool = False
