from __future__ import annotations

from .models import ExpertProfile


class ExpertRegistry:
    def __init__(self, profiles: tuple[ExpertProfile, ...] = ()) -> None:
        self._profiles = {profile.expert_id: profile for profile in profiles}

    def get(self, expert_id: str) -> ExpertProfile:
        return self._profiles[expert_id]

    def all(self) -> tuple[ExpertProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def for_domain(self, domain: str) -> tuple[ExpertProfile, ...]:
        return tuple(p for p in self.all() if domain in p.domains)


def default_registry() -> ExpertRegistry:
    """Map domain expertise onto agents that already exist in CK-NEXUS."""
    profiles = (
        ExpertProfile("director", "DirectorAgent", ("architecture", "business", "cross_domain")),
        ExpertProfile("engineer", "EngineerAgent", ("backend", "frontend", "data", "ai_ml", "devops")),
        ExpertProfile("guardian", "GuardianAgent", ("security", "reliability", "compliance")),
        ExpertProfile("analyst", "AnalystAgent", ("analysis", "data", "finance", "observability")),
        ExpertProfile("researcher", "ResearcherAgent", ("research", "legal", "standards")),
        ExpertProfile("designer", "DesignerAgent", ("ux", "frontend")),
        ExpertProfile("connector", "ConnectorAgent", ("integrations", "devops")),
        # This is an independent role contract, not an execution agent and not self-approval.
        ExpertProfile("independent_verifier", "IndependentVerifier", ("verification",), may_verify=True),
    )
    return ExpertRegistry(profiles)
