from __future__ import annotations

import re

from .models import ExpertRoute, RiskClass
from .registry import ExpertRegistry, default_registry


_DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "security": ("security", "vulnerability", "threat", "secret", "credential", "auth", "owasp"),
    "architecture": ("architecture", "system design", "distributed", "scalability"),
    "backend": ("backend", "api", "fastapi", "server", "runtime"),
    "frontend": ("frontend", "nuxt", "react", "web ui", "css"),
    "devops": ("devops", "docker", "kubernetes", "runner", "ci", "cd", "vps"),
    "data": ("database", "postgres", "redis", "sql", "data", "schema"),
    "ai_ml": ("ai", "model", "llm", "agent", "embedding", "rag"),
    "research": ("research", "ค้นหา", "วิจัย", "study"),
    "ux": ("ux", "ui", "accessibility", "design", "ออกแบบ"),
    "reliability": ("reliability", "recovery", "failure", "retry", "circuit breaker"),
    "observability": ("observability", "otel", "trace", "metric", "logging"),
    "compliance": ("compliance", "governance", "policy", "nist", "iso"),
    "legal": ("legal", "law", "license", "privacy", "กฎหมาย"),
    "finance": ("finance", "financial", "pricing", "roi", "cost", "ราคา"),
    "business": ("business", "product", "sales", "market", "ลูกค้า"),
    "integrations": ("integration", "connector", "mcp", "oauth", "webhook", "n8n"),
    "verification": ("verify", "verification", "evidence", "audit", "test", "ตรวจสอบ"),
}

_PRODUCTION_TERMS = ("production", "deploy", "release", "merge", "pr #14", "prod")
_HIGH_RISK_TERMS = (
    "delete",
    "destroy",
    "payment",
    "purchase",
    "credential",
    "secret",
    "private key",
    "send email",
    "external write",
    "permission",
    "authorize",
    "production mutation",
)

_PRIMARY_BY_DOMAIN = {
    "security": "guardian",
    "architecture": "director",
    "backend": "engineer",
    "frontend": "designer",
    "devops": "engineer",
    "data": "analyst",
    "ai_ml": "engineer",
    "research": "researcher",
    "ux": "designer",
    "reliability": "guardian",
    "observability": "analyst",
    "compliance": "guardian",
    "legal": "researcher",
    "finance": "analyst",
    "business": "director",
    "integrations": "connector",
    "verification": "independent_verifier",
}


def _contains(text: str, term: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) is not None


def _unique(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


class ExpertRouter:
    """Deterministic recommendation-only router.

    This layer cannot execute tools, grant permissions, mutate production, or
    upgrade evidence. High-risk routes explicitly require approval and an
    independent verifier.
    """

    def __init__(self, registry: ExpertRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def classify_domains(self, task: str) -> tuple[str, ...]:
        text = task.casefold()
        matches = [
            domain
            for domain, terms in _DOMAIN_TERMS.items()
            if any(_contains(text, term.casefold()) for term in terms)
        ]
        return tuple(matches)

    def classify_risk(self, task: str, domains: tuple[str, ...]) -> RiskClass:
        text = task.casefold()
        if any(_contains(text, term) for term in _PRODUCTION_TERMS):
            return RiskClass.PRODUCTION
        if any(_contains(text, term) for term in _HIGH_RISK_TERMS):
            return RiskClass.HIGH
        if {"security", "legal", "compliance"}.intersection(domains):
            return RiskClass.HIGH
        if len(domains) > 1:
            return RiskClass.MEDIUM
        return RiskClass.LOW

    def route(self, task: str) -> ExpertRoute:
        domains = self.classify_domains(task)
        needs_discovery = not domains
        routed_domains = domains or ("cross_domain",)
        risk = self.classify_risk(task, domains)

        primary = _PRIMARY_BY_DOMAIN.get(routed_domains[0], "director")
        support = [
            _PRIMARY_BY_DOMAIN.get(domain, "director") for domain in routed_domains[1:]
        ]

        if len(routed_domains) > 1 and primary != "director":
            support.append("director")
        if needs_discovery:
            support.append("researcher")

        independent_required = (
            risk in {RiskClass.HIGH, RiskClass.PRODUCTION} or "verification" in domains
        )
        if independent_required and primary != "independent_verifier":
            support.append("independent_verifier")
        if risk in {RiskClass.HIGH, RiskClass.PRODUCTION} and primary != "guardian":
            support.append("guardian")

        supporting = tuple(x for x in _unique(support) if x != primary)
        approval_required = risk in {RiskClass.HIGH, RiskClass.PRODUCTION}

        capabilities = _unique(
            capability
            for expert_id in (primary, *supporting)
            for capability in self.registry.get(expert_id).capabilities
        )

        rationale = [
            f"domains={','.join(domains) if domains else 'unknown'}",
            f"risk={risk.value}",
        ]
        if needs_discovery:
            rationale.append("unknown-domain: research before execution")
        if approval_required:
            rationale.append("bounded-autonomy: approval required before privileged execution")
        if independent_required:
            rationale.append("no-self-approval: independent verification required")

        return ExpertRoute(
            domains=domains,
            primary_expert=primary,
            supporting_experts=supporting,
            required_capabilities=capabilities,
            risk_class=risk,
            approval_required=approval_required,
            independent_verifier_required=independent_required,
            needs_discovery=needs_discovery,
            rationale=tuple(rationale),
        )
