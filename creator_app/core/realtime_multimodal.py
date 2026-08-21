from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RealtimeModality(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"


class RealtimeSession(BaseModel):
    session_id: str
    provider: str
    model: str
    input_modalities: set[RealtimeModality] = Field(default_factory=set)
    output_modalities: set[RealtimeModality] = Field(default_factory=set)
    supports_barge_in: bool = False
    supports_resumption: bool = False
    ephemeral_credential_ref: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    production_promotion_allowed: bool = False


class RealtimePolicy:
    @staticmethod
    def client_direct_connection_allowed(session: RealtimeSession) -> bool:
        return bool(session.ephemeral_credential_ref)

    @staticmethod
    def is_multimodal(session: RealtimeSession) -> bool:
        return len(session.input_modalities) > 1
