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
    mode: Literal["mock", "openai"]
    status: Literal["completed", "failed"]
    duration_ms: int
    created_at: datetime


class StatusResponse(BaseModel):
    name: str
    version: str
    mode: Literal["mock", "openai", "blocked"]
    model: str
    key_configured: bool
    database_ready: bool
    access_required: bool
    codex_enabled: bool
    codex_ready: bool
    codex_sandbox: Literal["read-only", "workspace-write"]


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
