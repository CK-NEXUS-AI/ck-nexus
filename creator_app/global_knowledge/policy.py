"""Fail-closed crawler policy gate.

This layer decides whether CK-NEXUS may crawl/ingest a resource. It does not
interpret robots.txt as authorization; it treats robots rules as one required
crawler-control signal alongside terms, privacy, and jurisdiction checks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CrawlPolicyInput:
    public_resource: bool
    robots_allowed: bool | None
    terms_allowed: bool | None
    jurisdiction_allowed: bool | None
    contains_sensitive_personal_data: bool = False
    explicit_data_permission: bool = False


@dataclass(frozen=True, slots=True)
class IngestDecision:
    allowed: bool
    code: str
    reasons: tuple[str, ...]


def evaluate_crawl_policy(value: CrawlPolicyInput) -> IngestDecision:
    reasons: list[str] = []

    if not value.public_resource:
        reasons.append("resource_not_public")

    if value.robots_allowed is not True:
        reasons.append(
            "robots_unknown" if value.robots_allowed is None else "robots_disallowed"
        )

    if value.terms_allowed is not True:
        reasons.append(
            "terms_unknown" if value.terms_allowed is None else "terms_disallowed"
        )

    if value.jurisdiction_allowed is not True:
        reasons.append(
            "jurisdiction_unknown"
            if value.jurisdiction_allowed is None
            else "jurisdiction_disallowed"
        )

    if value.contains_sensitive_personal_data and not value.explicit_data_permission:
        reasons.append("sensitive_personal_data_without_permission")

    if reasons:
        return IngestDecision(False, "BLOCKED_POLICY", tuple(reasons))

    return IngestDecision(True, "ALLOWED", ())
