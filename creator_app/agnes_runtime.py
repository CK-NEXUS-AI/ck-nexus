from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from creator_app.agnes.execution.adapters.linux_namespace_sandbox import (
    LinuxNamespaceSandboxExecutor,
)
from creator_app.agnes.execution.approval import StickyApprovalResolver
from creator_app.agnes.execution.dispatcher import (
    DispatcherPolicy,
    SkillExecutionDispatcher,
    build_phase1_dispatcher,
)
from creator_app.agnes.execution.guards import ExecutionPolicyEngine
from creator_app.agnes.execution.idempotency import SQLiteIdempotencyStore
from creator_app.agnes.execution.phase3 import (
    AutonomousDevController,
    RedisIdempotencyStore,
    WorkspaceLifecycleManager,
)
from creator_app.agnes.execution.phase3.hardening import CgroupV2Manager
from creator_app.agnes.execution.phase3.sandbox import HardenedLinuxNamespaceRunner
from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest
from creator_app.agnes.execution.result import SkillExecutionResult
from creator_app.agnes.execution.sandbox import (
    LinuxNamespaceRunner,
    SandboxPolicy,
    SandboxWorkspaceManager,
)
from creator_app.agnes_discovery import SkillDiscoveryPolicy
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_skills import AgnesSkillRegistry, SkillDefinition, SkillRisk
from creator_app.agnes_workbench import WorkspaceBroker, WorkspaceKind
from creator_app.credential_broker import CredentialBroker
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
        credential_broker: CredentialBroker | None = None,
        dispatcher: SkillExecutionDispatcher | None = None,
        sandbox_enabled: bool = False,
        sandbox_root: Path | None = None,
        sandbox_repository_root: Path | None = None,
        phase3_enabled: bool = False,
        environment: str = "development",
        phase3_redis_url: str = "",
        phase3_cgroup_root: Path = Path("/sys/fs/cgroup"),
    ) -> None:
        self.skill_file = skill_file
        self.registry = AgnesSkillRegistry.load(skill_file)
        self.ledger = AppendOnlyLedger(ledger_path)
        self.provider_router = provider_router
        self.policy = policy or AgnesPolicy()
        self.workspace_broker = WorkspaceBroker()
        self.discovery = SkillDiscoveryPolicy()
        self.approvals = StickyApprovalResolver()
        self.dev_controller: AutonomousDevController | None = None
        if dispatcher is not None:
            self.dispatcher = dispatcher
        elif sandbox_enabled:
            sandbox_root = (sandbox_root or (ledger_path.parent / "agnes-sandbox")).resolve()
            repository_root = (sandbox_repository_root or Path.cwd()).resolve()
            normalized_environment = environment.strip().lower() or "development"
            cgroups = CgroupV2Manager(root=phase3_cgroup_root) if phase3_enabled else None
            if phase3_enabled and normalized_environment in {"staging", "production"}:
                if not phase3_redis_url:
                    raise RuntimeError(
                        "distributed_idempotency_required: "
                        "CKNEXUS_AGNES_REDIS_URL is not configured"
                    )
                if not phase3_redis_url.startswith(("redis://", "rediss://")):
                    raise RuntimeError(
                        "distributed_idempotency_required: unsupported Redis URL scheme"
                    )
                try:
                    from redis.asyncio import Redis
                except ImportError as exc:
                    raise RuntimeError(
                        "distributed_idempotency_required: redis client is unavailable"
                    ) from exc
                redis_client = Redis.from_url(
                    phase3_redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,
                )
                idempotency = RedisIdempotencyStore(redis_client)
                if not cgroups or not cgroups.health().get("ready"):
                    raise RuntimeError(
                        "cgroup_v2_enforcement_required: delegated writable cgroup v2 "
                        "root is unavailable"
                    )
            else:
                idempotency = SQLiteIdempotencyStore(sandbox_root / "idempotency.sqlite3")
            self.dispatcher = SkillExecutionDispatcher(
                skill_registry=self.registry,
                policy_engine=ExecutionPolicyEngine(self.policy),
                approval_service=self.approvals,
                ledger=self.ledger,
                credential_broker=credential_broker,
                idempotency_store=idempotency,
                dispatcher_policy=DispatcherPolicy(
                    require_durable_idempotency_for_high_risk=True,
                    require_distributed_idempotency_for_staging_and_production=True,
                ),
            )
            sandbox_policy = SandboxPolicy(
                base_dir=sandbox_root,
                repository_root=repository_root,
            )
            workspace_manager = SandboxWorkspaceManager(sandbox_policy)
            if phase3_enabled:
                assert cgroups is not None
                runner = HardenedLinuxNamespaceRunner(sandbox_policy, cgroups=cgroups)
            else:
                runner = LinuxNamespaceRunner(sandbox_policy)
            self.dispatcher.register(LinuxNamespaceSandboxExecutor(workspace_manager, runner))
            if phase3_enabled:
                self.dev_controller = AutonomousDevController(
                    agnes=self,
                    workspaces=WorkspaceLifecycleManager(workspace_manager),
                    ledger=self.ledger,
                    approvals=self.approvals,
                )
        else:
            self.dispatcher = build_phase1_dispatcher(
                skill_registry=self.registry,
                policy_engine=ExecutionPolicyEngine(self.policy),
                approval_service=self.approvals,
                ledger=self.ledger,
                credential_broker=credential_broker,
            )

    def _inference_status(self) -> dict[str, object]:
        if self.provider_router is None:
            return {"mode": "unconfigured", "ready": False, "provider": None}
        statuses = self.provider_router.statuses()
        local = next(
            (
                status
                for status in statuses
                if status.kind in {ProviderKind.LOCAL, ProviderKind.MOCK}
                and status.available
                and not status.circuit_open
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
            "execution_kernel": self.dispatcher.status(),
            "autonomous_dev_pipeline": {
                "enabled": self.dev_controller is not None,
                "auto_merge": False,
                "production_deploy": False,
            },
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
        if (
            environment == "production"
            and skill.risk is not SkillRisk.READ_ONLY
            and not self.policy.allow_production_mutation
        ):
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

    async def execute_skill(
        self,
        plan_step: Mapping[str, Any],
        *,
        goal: str,
        correlation_id: str,
        tenant_id: str = "default",
        actor_id: str = "system",
        environment: str = "development",
        workspace_id: str | None = None,
        baseline_commit: str | None = None,
        approval_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> SkillExecutionResult:
        skill_id = str(plan_step.get("id") or plan_step.get("skill_id") or "").strip()
        skill = self.registry.get(skill_id)
        executor = ExecutorType(str(plan_step.get("executor") or skill.executor))
        execution_id = str(plan_step.get("execution_id") or f"agnes_exec_{uuid4().hex}")
        if executor is ExecutorType.SANDBOX and workspace_id is None:
            workspace_id = execution_id
        request = SkillExecutionRequest(
            execution_id=execution_id,
            correlation_id=correlation_id,
            skill_id=skill.id,
            skill_version=str(plan_step.get("version") or skill.version),
            executor=executor,
            goal=goal,
            plan_step=plan_step,
            inputs=plan_step.get("inputs", {}),
            tenant_id=tenant_id,
            actor_id=actor_id,
            environment=environment,
            policy_version=str(plan_step.get("policy_version") or "r14-phase1"),
            workspace_id=workspace_id,
            baseline_commit=baseline_commit,
            requires_approval=bool(plan_step.get("requires_approval", False)),
            approval_id=approval_id,
            timeout_seconds=int(plan_step.get("timeout_seconds", 300)),
            idempotency_key=idempotency_key,
            allowlist_paths=tuple(plan_step.get("allowlist_paths", ())),
            granted_capabilities=tuple(plan_step.get("granted_capabilities", ())),
        )
        return await self.dispatcher.execute(request)

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
