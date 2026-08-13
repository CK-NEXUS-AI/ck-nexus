from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    category: str
    priority: str
    matched_rule: str
    reasons: tuple[str, ...]


_ALIAS_RULES = {
    "security": "SECURITY",
    "billing": "BILLING",
    "github": "DEVOPS",
    "alerts": "SYSTEM_ALERT",
    "support": "SUPPORT",
    "ai": "AI_REQUEST",
}

_SECURITY_TERMS = ("security", "breach", "phishing", "malware", "credential", "vulnerability")
_BILLING_TERMS = ("invoice", "payment", "billing", "charge", "refund")
_DEVOPS_TERMS = ("github", "ci", "build failed", "deployment", "production error")
_ALERT_TERMS = ("alert", "incident", "downtime", "service unavailable")
_SUPPORT_TERMS = ("support", "help", "problem", "issue")
_AI_TERMS = ("ai request", "generate", "summarize", "rewrite")


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    value = text.casefold()
    return any(term.casefold() in value for term in terms)


def route_email(
    *,
    matched_alias: str | None,
    subject: str,
    sender: str = "",
    quarantined: bool = False,
) -> RoutingDecision:
    """Deterministic, versionable P0 router. No model call is permitted here."""
    if quarantined:
        return RoutingDecision("QUARANTINE", "critical", "R-000", ("attachment_or_policy_quarantine",))

    alias_local = ""
    if matched_alias:
        alias_local = matched_alias.strip().casefold().split("@", 1)[0]

    # Security always wins over other business routes.
    combined = f"{subject}\n{sender}"
    if alias_local == "security" or _contains_any(combined, _SECURITY_TERMS):
        return RoutingDecision("SECURITY", "critical", "R-100", ("security_signal",))

    alias_category = _ALIAS_RULES.get(alias_local)
    if alias_category:
        priority = "high" if alias_category in {"BILLING", "DEVOPS", "SYSTEM_ALERT"} else "normal"
        return RoutingDecision(alias_category, priority, f"R-ALIAS-{alias_local.upper()}", (f"alias:{alias_local}",))

    ordered = (
        ("BILLING", _BILLING_TERMS, "R-200", "high"),
        ("DEVOPS", _DEVOPS_TERMS, "R-300", "high"),
        ("SYSTEM_ALERT", _ALERT_TERMS, "R-400", "high"),
        ("SUPPORT", _SUPPORT_TERMS, "R-500", "normal"),
        ("AI_REQUEST", _AI_TERMS, "R-600", "normal"),
    )
    for category, terms, rule, priority in ordered:
        if _contains_any(combined, terms):
            return RoutingDecision(category, priority, rule, ("subject_or_sender_keyword",))

    return RoutingDecision("UNKNOWN", "normal", "R-999", ("no_rule_matched",))
