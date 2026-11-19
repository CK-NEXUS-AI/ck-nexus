"""Purpose-bound Gmail policy enforcement."""

from __future__ import annotations

from creator_app.personal_intelligence import ConsentLedger, PersonalCapability

from .contracts import GmailCapability, GmailPolicyRequest, GmailPurpose


class GmailPolicyDenied(PermissionError):
    """Raised when a Gmail action lacks consent or explicit write approval."""


_READ_CAPABILITIES = frozenset(
    {
        GmailCapability.METADATA_READ,
        GmailCapability.BODY_READ,
        GmailCapability.ATTACHMENT_READ,
        GmailCapability.SEARCH,
    }
)

_PURPOSE_CAPABILITIES: dict[GmailPurpose, frozenset[GmailCapability]] = {
    GmailPurpose.INBOX_SUMMARY: frozenset(
        {GmailCapability.METADATA_READ, GmailCapability.BODY_READ, GmailCapability.SEARCH}
    ),
    GmailPurpose.THREAD_CONTEXT: frozenset(
        {GmailCapability.METADATA_READ, GmailCapability.BODY_READ}
    ),
    GmailPurpose.REPLY_DRAFT: frozenset(
        {GmailCapability.METADATA_READ, GmailCapability.BODY_READ, GmailCapability.DRAFT_CREATE}
    ),
    GmailPurpose.SEND_APPROVED_REPLY: frozenset(
        {GmailCapability.DRAFT_CREATE, GmailCapability.SEND}
    ),
    GmailPurpose.PROFILE_LEARNING: frozenset(
        {GmailCapability.BODY_READ, GmailCapability.PROFILE_LEARN}
    ),
    GmailPurpose.ATTACHMENT_ANALYSIS: frozenset(
        {GmailCapability.ATTACHMENT_READ, GmailCapability.BODY_READ}
    ),
}


def authorize_gmail(request: GmailPolicyRequest, consent: ConsentLedger) -> dict[str, object]:
    """Return a redacted authorization receipt or fail closed."""
    allowed_for_purpose = _PURPOSE_CAPABILITIES.get(request.purpose, frozenset())
    if request.capability not in allowed_for_purpose:
        raise GmailPolicyDenied("capability is not allowed for the requested purpose")

    if request.capability in _READ_CAPABILITIES:
        consent.require(PersonalCapability.GMAIL_READ)

    if request.capability == GmailCapability.PROFILE_LEARN:
        consent.require(PersonalCapability.GMAIL_READ)
        consent.require(PersonalCapability.PROFILE_LEARN)

    if request.capability == GmailCapability.DRAFT_CREATE:
        consent.require(PersonalCapability.GMAIL_READ)
        consent.require(PersonalCapability.GMAIL_SEND)
        if not request.approved_write:
            raise GmailPolicyDenied("draft creation requires explicit external-write approval")

    if request.capability == GmailCapability.SEND:
        consent.require(PersonalCapability.GMAIL_SEND)
        if not request.approved_send:
            raise GmailPolicyDenied("sending email requires explicit send approval")

    return {
        "capability": request.capability.value,
        "purpose": request.purpose.value,
        "authorized": True,
        "approved_write": request.approved_write,
        "approved_send": request.approved_send,
        "authority": "CK-NEXUS",
        "raw_credential_exposed": False,
    }
