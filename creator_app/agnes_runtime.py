from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from creator_app.agnes_discovery import SkillDiscoveryPolicy
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_skills import AgnesSkillRegistry, SkillDefinition, SkillRisk
from creator_app.agnes_workbench import WorkspaceBroker, WorkspaceKind
from creator_app.provider_router import ProviderKind, ProviderRouter


@dataclass(frozen=True, slots=True)
class AgnesPolicy:
    append_only: bool = True
    allow_user_api_keys: bool = False
    prefer_local_runtime: bool = True
    allow_production_mutation: bool = False
    external_write_requires_approval: bool = True
    high_impact_requires_approval: bool = True
    max_parallel_skills: int = 5

    def as_dict(self) -> dict[str, object]:
        return {
            "append_only": self.append_only,
            "allow_user_api_keys": self.allow_user_api_keys,
            "prefer_local_runtime": self.prefer_local_runtime,
            "allow_production_mutation": self.allow_production_mutation,
            "external_write_requires_approval": self.external_write_requires_approval,
            "high_impact_requires_approval": self.high_impact_requires_approval,
            "max_parallel_skills": self.max_parallel_skills,
        }


class AgnesPolicyViolation(PermissionError):
    pass


class AgnesNervousSystem:
    def __init__(
        self,
        *,
        skill_file: Path,
        ledger_path: Path,
        provider_router: ProviderRouter | None = None,
        policy: AgnesPolicy | None = None,
    ) -> None:
        self.skill_file = skill_file
        self.registry = AgnesSkillRegistry.load(skill_file)
        self.ledger = AppendOnlyLedger(ledger_path)
        self.provider_router = provider_router
        self.policy = policy or AgnesPolicy()
        self.workspace_broker = WorkspaceBroker()
        self.discovery = SkillDiscoveryPolicy()

    def _inference_status(self) -> dict[str, object]:
        if self.provider_router is None:
            return {"mode": "unconfigured", "ready": False, "provider": None}
        statuses = self.provider_router.statuses()
        local = next(
            (
                status for status in statuses
                if status.kind in {ProviderKind.LOCAL, ProviderKind.MOCK}
                and status.available and not status.circuit_open
            ),
            None,
        )
        if local is not None:
            return {"mode": "local_or_mock", "ready": True, "provider": local.name}
        return {
            "mode": "blocked_without_local_runtime",
            "ready": False,
            "provider": None,
            "reason": "AGNES local-first path will not consume a user API key.",
        }

    def status(self) -> dict[str, object]:
        ledger = self.ledger.verify()
        return {
            "agent": self.registry.manifest.agent,
            "skill_manifest_version": self.registry.manifest.manifest_version,
            "skill_count": len(self.registry.all()),
            "policy": self.policy.as_dict(),
            "inference": self._inference_status(),
            "ledger": ledger.as_dict(),
            "workspace_providers": [item.as_dict() for item in self.workspace_broker.providers()],
            "discovery_sources": self.discovery.source_catalog(),
            "production_gate": "NO-GO until R12 staging evidence passes",
        }

    def skills(self) -> list[dict[str, object]]:
        return [skill.as_dict() for skill in self.registry.all()]

    def plan(self, goal: str) -> dict[str, object]:
        selected = self.registry.select(goal, limit=self.policy.max_parallel_skills)
        requires_approval = any(
            skill.approval_required
            or skill.risk in {SkillRisk.EXTERNAL_WRITE, SkillRisk.HIGH_IMPACT}
            for skill in selected
        )
        return {
            "plan_id": f"agnes_plan_{uuid4().hex}",
            "goal": goal,
            "skills": [skill.as_dict() for skill in selected],
            "requires_approval": requires_approval,
            "inference": self._inference_status(),
            "workspace": self.workspace_broker.plan(preferred=WorkspaceKind.LOCAL),
        }

    def authorize_skill(
        self,
        skill: SkillDefinition,
        *,
        environment: str,
        approved: bool,
        uses_user_api_key: bool = False,
    ) -> None:
        if uses_user_api_key and not self.policy.allow_user_api_keys:
            raise AgnesPolicyViolation("AGNES is not allowed to consume user API keys.")
        if environment == "production" and skill.risk is not SkillRisk.READ_ONLY:
            if not self.policy.allow_production_mutation:
                raise AgnesPolicyViolation("AGNES production mutation is disabled.")
        if skill.risk in {SkillRisk.EXTERNAL_WRITE, SkillRisk.HIGH_IMPACT} and not approved:
            raise AgnesPolicyViolation("This AGNES skill requires explicit approval.")

    def record_learning(
        self,
        *,
        subject: str,
        summary: str,
        sources: list[str],
        supersedes: list[str] | None = None,
    ) -> dict[str, object]:
        return self.ledger.append(
            "knowledge_learned",
            {
                "subject": subject,
                "summary": summary,
                "sources": sources,
                "supersedes": supersedes or [],
                "preservation_rule": "append_only_no_historical_delete",
            },
        )


    def discovery_sources(self) -> list[dict[str, object]]:
        return self.discovery.source_catalog()

    def model_watch_plan(self, *, limit: int = 50) -> dict[str, object]:
        return self.discovery.model_watch_plan(limit)

    def self_upgrade_plan(self, goal: str) -> dict[str, object]:
        steps = [
            "discover trusted sources / skills / tools",
            "capture source identity, license, version, checksum and provenance",
            "quarantine unknown or community skill code",
            "verify claims against primary sources",
            "compare capability with current CK-NEXUS baseline",
            "classify risk, required permissions, credentials and network egress",
            "produce upgrade proposal and acceptance criteria",
            "create isolated workspace from exact baseline commit",
            "create feature branch without rewriting existing history",
            "activate only task-scoped skills/tools",
            "implement bounded change",
            "compile and run targeted tests",
            "run non-billing regression tests",
            "run secret, dependency and defensive security scans",
            "benchmark/evaluate behavior and resource use",
            "build machine-readable evidence and rollback plan",
            "Development Council review",
            "request approval for merge/canary when high-impact",
            "run canary and observe health/metrics/logs/traces",
            "rollback on failed canary or violated SLO",
            "append verified learning and supersession links; never delete old evidence",
        ]
        return {
            "upgrade_id": f"agnes_upgrade_{uuid4().hex}",
            "goal": goal,
            "steps": [{"index": i, "step": step} for i, step in enumerate(steps, 1)],
            "safe_auto_boundary": 17,
            "approval_boundary": "merge/canary/external/high-impact actions",
            "history_policy": "append-only; protected history is never rewritten",
            "production_gate": "R12 remains mandatory",
        }
