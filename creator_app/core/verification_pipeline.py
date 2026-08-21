from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class VerificationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


class VerificationCheck(BaseModel):
    name: str
    status: VerificationStatus
    evidence_ids: list[str] = Field(default_factory=list)
    details: str = ""


class VerificationReport(BaseModel):
    subject: str
    checks: list[VerificationCheck] = Field(default_factory=list)
    production_promotion_allowed: bool = False

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(
            check.status == VerificationStatus.PASS and check.evidence_ids
            for check in self.checks
        )


class VerificationPipeline:
    """Fail-closed aggregation of independently produced verification checks."""

    def build_report(
        self,
        *,
        subject: str,
        checks: list[VerificationCheck],
    ) -> VerificationReport:
        return VerificationReport(
            subject=subject,
            checks=list(checks),
            production_promotion_allowed=False,
        )
