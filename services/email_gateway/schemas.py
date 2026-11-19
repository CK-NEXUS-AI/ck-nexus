from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EmailIngressRequest(BaseModel):
    mailbox: str = Field(min_length=3, max_length=320)
    provider: Literal["gmail", "outlook", "imap"]
    provider_message_id: str = Field(min_length=1, max_length=512)
    internet_message_id: str | None = Field(default=None, max_length=998)
    execution_id: str = Field(min_length=1, max_length=256)


class EmailIngressResult(BaseModel):
    status: Literal["accepted", "duplicate"]
    journal_id: str | None
    duplicate_reason: str | None = None


class OutboxRequest(BaseModel):
    journal_id: str
    action_type: str = Field(min_length=1, max_length=128)
    destination: str = Field(min_length=1, max_length=512)
    payload: dict[str, Any]
    deduplication_key: str = Field(min_length=8, max_length=512)


class OutboxResult(BaseModel):
    created: bool
    outbox_id: str


class RoutingRequest(BaseModel):
    matched_alias: str | None = Field(default=None, max_length=320)
    subject: str = Field(default="", max_length=998)
    sender: str = Field(default="", max_length=998)
    quarantined: bool = False


class RoutingResult(BaseModel):
    category: str
    priority: str
    matched_rule: str
    reasons: list[str]


class LoopCheckRequest(BaseModel):
    headers: dict[str, str]
    system_addresses: list[str] = []


class LoopCheckResult(BaseModel):
    allow_automatic_reply: bool
    reason: str


class OutboxClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=256)
    limit: int = Field(default=20, ge=1, le=100)
    lease_seconds: int = Field(default=120, ge=30, le=3600)


class OutboxClaimItem(BaseModel):
    id: str
    email_journal_id: str
    action_type: str
    destination: str
    payload: dict[str, Any]
    deduplication_key: str
    attempt_count: int


class OutboxClaimResult(BaseModel):
    items: list[OutboxClaimItem]


class OutboxSentRequest(BaseModel):
    provider_message_id: str | None = Field(default=None, max_length=512)


class OutboxRetryRequest(BaseModel):
    error: str = Field(min_length=1, max_length=2000)


class LeaseRecoveryResult(BaseModel):
    journal: int
    outbox: int
