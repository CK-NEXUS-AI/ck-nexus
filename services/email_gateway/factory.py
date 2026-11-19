from __future__ import annotations

from pathlib import Path
from typing import Any

from services.email_gateway.repository import EmailGatewayRepository


def create_email_repository(*, database_url: str = "", database_path: Path) -> Any:
    value = database_url.strip()
    if value.startswith(("postgresql://", "postgres://")):
        from services.email_gateway.postgres_repository import PostgresEmailGatewayRepository

        return PostgresEmailGatewayRepository(value)
    if value and not value.startswith("sqlite://"):
        raise ValueError("Unsupported CKNEXUS_EMAIL_DATABASE_URL scheme")
    if value.startswith("sqlite:///"):
        database_path = Path(value.removeprefix("sqlite:///"))
    return EmailGatewayRepository(database_path)
