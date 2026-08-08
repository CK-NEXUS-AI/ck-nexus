from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayError(Exception):
    code: str
    message: str
    status_code: int
    retryable: bool = False

    def public(self, correlation_id: str) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "correlation_id": correlation_id,
                "retryable": self.retryable,
            }
        }
