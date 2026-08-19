"""Governed Gmail service wrapping an injected OAuth-backed transport."""

from __future__ import annotations

import hashlib

from creator_app.personal_intelligence import ConsentLedger
from creator_app.privacy_firewall import ContentEnvelope, DataClassification, TrustLevel

from .contracts import (
    GmailBackend,
    GmailCapability,
    GmailMessageMetadata,
    GmailPolicyRequest,
    GmailPurpose,
)
from .policy import authorize_gmail


class GovernedGmailService:
    """Apply purpose/consent/write gates before touching the Gmail transport."""

    def __init__(self, *, backend: GmailBackend, consent: ConsentLedger) -> None:
        self._backend = backend
        self._consent = consent

    def list_metadata(
        self,
        *,
        query: str,
        limit: int = 20,
        purpose: GmailPurpose = GmailPurpose.INBOX_SUMMARY,
    ) -> tuple[GmailMessageMetadata, ...]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        authorize_gmail(
            GmailPolicyRequest(GmailCapability.METADATA_READ, purpose),
            self._consent,
        )
        return self._backend.list_metadata(query, limit)

    def read_body(
        self,
        message_id: str,
        *,
        purpose: GmailPurpose,
    ) -> ContentEnvelope:
        if not message_id.strip():
            raise ValueError("message_id must not be empty")
        authorize_gmail(
            GmailPolicyRequest(GmailCapability.BODY_READ, purpose),
            self._consent,
        )
        body = self._backend.read_body(message_id)
        return ContentEnvelope(
            source=f"gmail:{message_id}",
            content=body,
            classification=DataClassification.PERSONAL,
            trust=TrustLevel.UNTRUSTED,
            purpose=purpose.value,
            taints=frozenset({"source:gmail", "untrusted:external_sender"}),
        )

    def create_draft(
        self,
        *,
        thread_id: str,
        body: str,
        approved_write: bool,
    ) -> dict[str, object]:
        if not thread_id.strip() or not body.strip():
            raise ValueError("thread_id and body must not be empty")
        receipt = authorize_gmail(
            GmailPolicyRequest(
                GmailCapability.DRAFT_CREATE,
                GmailPurpose.REPLY_DRAFT,
                approved_write=approved_write,
            ),
            self._consent,
        )
        draft_id = self._backend.create_draft(thread_id, body)
        return {
            **receipt,
            "draft_id": draft_id,
            "body_digest": hashlib.sha256(body.encode()).hexdigest(),
            "body_persisted_in_receipt": False,
        }

    def send_draft(self, draft_id: str, *, approved_send: bool) -> dict[str, object]:
        if not draft_id.strip():
            raise ValueError("draft_id must not be empty")
        receipt = authorize_gmail(
            GmailPolicyRequest(
                GmailCapability.SEND,
                GmailPurpose.SEND_APPROVED_REPLY,
                approved_send=approved_send,
            ),
            self._consent,
        )
        message_id = self._backend.send_draft(draft_id)
        return {
            **receipt,
            "draft_id": draft_id,
            "sent_message_id": message_id,
        }
