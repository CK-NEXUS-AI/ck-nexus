"""CK-NEXUS governed Gmail integration contracts."""

from .attachments import AttachmentDecision, evaluate_attachment
from .contracts import (
    GmailBackend,
    GmailCapability,
    GmailMessageMetadata,
    GmailPolicyRequest,
    GmailPurpose,
)
from .policy import GmailPolicyDenied, authorize_gmail
from .service import GovernedGmailService

__all__ = [
    "AttachmentDecision",
    "GmailBackend",
    "GmailCapability",
    "GmailMessageMetadata",
    "GmailPolicyDenied",
    "GmailPolicyRequest",
    "GmailPurpose",
    "GovernedGmailService",
    "authorize_gmail",
    "evaluate_attachment",
]
