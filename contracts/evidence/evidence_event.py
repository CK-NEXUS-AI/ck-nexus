from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    attempt: int = Field(ge=0)
    event_type: Literal[
        "authorized", "execution_started", "execution_finished",
        "verification_started", "verification_finished", "policy_denied",
        "budget_denied", "error"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    redacted_metadata: dict[str, str] = {}
    occurred_at: datetime


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    authority_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_id: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)
    created_at: datetime
    signature: str | None = None
