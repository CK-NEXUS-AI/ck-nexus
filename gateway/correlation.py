from __future__ import annotations

import uuid

HEADER = "X-CK-Correlation-ID"


def normalize_correlation_id(value: str | None) -> str:
    if value:
        candidate = value.strip()
        try:
            parsed = uuid.UUID(candidate)
            return str(parsed)
        except (ValueError, AttributeError):
            pass
    return str(uuid.uuid4())
