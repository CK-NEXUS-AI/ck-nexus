"""Granular Gmail capability and purpose contracts for CK-NEXUS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class GmailCapability(StrEnum):
    METADATA_READ = "gmail.metadata.read"
    BODY_READ = "gmail.body.read"
    ATTACHMENT_READ = "gmail.attachment.read"
    SEARCH = "gmail.search"
    DRAFT_CREATE = "gmail.draft.create"
    SEND = "gmail.send"
    PROFILE_LEARN = "gmail.profile.learn"


class GmailPurpose(StrEnum):
    INBOX_SUMMARY = "inbox_summary"
    THREAD_CONTEXT = "thread_context"
    REPLY_DRAFT = "reply_draft"
    SEND_APPROVED_REPLY = "send_approved_reply"
    PROFILE_LEARNING = "profile_learning"
    ATTACHMENT_ANALYSIS = "attachment_analysis"


@dataclass(frozen=True, slots=True)
class GmailPolicyRequest:
    capability: GmailCapability
    purpose: GmailPurpose
    approved_write: bool = False
    approved_send: bool = False


@dataclass(frozen=True, slots=True)
class GmailMessageMetadata:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    received_at: str


class GmailBackend(Protocol):
    """Transport boundary. Implementations own OAuth and credential leases."""

    def list_metadata(self, query: str, limit: int) -> tuple[GmailMessageMetadata, ...]: ...

    def read_body(self, message_id: str) -> str: ...

    def create_draft(self, thread_id: str, body: str) -> str: ...

    def send_draft(self, draft_id: str) -> str: ...
