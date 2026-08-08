"""Reliable email-ingress primitives for CK-NEXUS P0."""

from services.email_gateway.repository import (
    ClaimResult,
    EmailGatewayRepository,
    OutboxItem,
)

__all__ = ["ClaimResult", "EmailGatewayRepository", "OutboxItem"]
