from __future__ import annotations

from services.email_gateway.repository import ClaimResult


def claim_email_once(
    repository,
    *,
    mailbox: str,
    provider: str,
    provider_message_id: str,
    execution_id: str,
    internet_message_id: str | None = None,
    lease_seconds: int = 300,
) -> ClaimResult:
    """Shared FastAPI/n8n atomic-claim boundary.

    Hard identity is (mailbox, provider, provider_message_id). Internet Message-ID
    is correlation metadata only and is never trusted as the primary dedup key.
    """
    return repository.claim_message(
        mailbox=mailbox,
        provider=provider,
        provider_message_id=provider_message_id,
        internet_message_id=internet_message_id,
        claimed_by=execution_id,
        lease_seconds=lease_seconds,
    )
