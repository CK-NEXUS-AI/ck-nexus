from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_skills import AgnesSkillRegistry
from creator_app.credential_broker import CredentialBroker

from .adapters.base import ExecutionContext, SkillExecutor
from .approval import StickyApprovalResolver
from .capabilities import CapabilityResolutionError, CapabilityResolver
from .credentials import CredentialLeaseService
from .evidence import EvidenceBuilder, redact
from .guards import ExecutionPolicyEngine, RiskClassifier
from .idempotency import IdempotencyState, IdempotencyStore, InMemoryIdempotencyStore
from .kill_switch import KillSwitchHierarchy
from .manifest import ImmutableExecutionManifest
from .permissions import PermissionResolver
from .registry import ExecutorRegistry
from .request import ExecutorRiskClass, SkillExecutionRequest
from .result import ExecutionStatus, SkillExecutionResult
from .verification import ResultVerifier


@dataclass(slots=True)
class DispatcherPolicy:
    require_durable_idempotency_for_high_risk: bool = True
    require_distributed_idempotency_for_staging_and_production: bool = True
    require_authenticated_approval_for_high_risk: bool = False


class SkillExecutionDispatcher:
    """Fail-closed AGNES Phase-1 control plane. No sandbox executor is bundled yet."""

    def __init__(
        self,
        *,
        skill_registry: AgnesSkillRegistry,
        policy_engine: ExecutionPolicyEngine,
        approval_service: StickyApprovalResolver,
        ledger: AppendOnlyLedger,
        credential_broker: CredentialBroker | None,
        kill_switches: KillSwitchHierarchy | None = None,
        idempotency_store: IdempotencyStore | None = None,
        dispatcher_policy: DispatcherPolicy | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.policy = policy_engine
        self.approval = approval_service
        self.ledger = ledger
        self.credentials = CredentialLeaseService(credential_broker)
        self.kill_switches = kill_switches or KillSwitchHierarchy()
        self.idempotency = idempotency_store or InMemoryIdempotencyStore()
        self.dispatcher_policy = dispatcher_policy or DispatcherPolicy()
        self.capabilities = CapabilityResolver()
        self.permissions = PermissionResolver()
        self.risk_classifier = RiskClassifier()
        self.verifier = ResultVerifier()
        self.executors = ExecutorRegistry()
        self.evidence = EvidenceBuilder(ledger)

    def register(self, executor: SkillExecutor) -> None:
        self.executors.register(executor)

    def status(self) -> dict[str, object]:
        executor_status = self.executors.status()
        sandbox_enabled = bool(executor_status.get("registered", {}).get("sandbox"))
        return {
            "phase": (
                "AGNES Execution Kernel Phase 2 — Isolated Sandbox Baseline"
                if sandbox_enabled
                else "AGNES Execution Kernel Phase 1 — Security Baseline"
            ),
            "agent_is_executor": False,
            "workspace_is_sandbox": sandbox_enabled,
            "sandbox_executor_enabled": sandbox_enabled,
            "fail_closed": True,
            "idempotency": {
                "backend": type(self.idempotency).__name__,
                "durable": self.idempotency.durable,
                "distributed": self.idempotency.distributed,
                "production_safe": self.idempotency.production_safe,
            },
            "executors": executor_status,
            "authenticated_approval_for_high_risk": (
                self.dispatcher_policy.require_authenticated_approval_for_high_risk
            ),
            "production_execution": "blocked_until_R12_and_production_safe_sandbox_evidence",
        }

    async def execute(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        start = time.monotonic()
        manifest: ImmutableExecutionManifest | None = None
        approval_fingerprint: str | None = None
        idempotency_claimed = False
        try:
            skill = self.skill_registry.get(request.skill_id)
            if skill.version != request.skill_version:
                return self._blocked(request, "skill_version_mismatch", start=start)
            try:
                capability = self.capabilities.resolve(request, skill)
            except CapabilityResolutionError as exc:
                return self._blocked(request, str(exc), start=start)

            kill_reason = self.kill_switches.reason(request)
            if kill_reason:
                return self._blocked(request, kill_reason, start=start)

            # Risk uses the skill/capability floor before executor resolution. This prevents
            # a lower-risk executor declaration from downgrading a risky skill.
            risk = self.risk_classifier.classify(skill)
            approval_fingerprint = self.approval.fingerprint(request, risk)
            manifest = ImmutableExecutionManifest.freeze(
                request,
                risk_class=risk,
                approval_fingerprint=approval_fingerprint,
            )

            decision = self.policy.evaluate(request, skill=skill, risk_class=risk)
            if not decision.allowed:
                return self._blocked(
                    request,
                    decision.reason,
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                )

            permission = self.permissions.evaluate(request, capability, risk)
            if not permission.allowed:
                suffix = ",".join(permission.missing)
                reason = f"{permission.reason}:{suffix}" if suffix else permission.reason
                return self._blocked(
                    request,
                    reason,
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                )

            require_authenticated_approval = (
                self.dispatcher_policy.require_authenticated_approval_for_high_risk
                and risk.rank >= ExecutorRiskClass.HIGH.rank
            )
            if decision.requires_approval and not self.approval.is_approved(
                approval_id=request.approval_id,
                fingerprint=approval_fingerprint,
                require_authenticated=require_authenticated_approval,
            ):
                return self._blocked(
                    request,
                    (
                        "authenticated_approval_required_or_mismatch"
                        if require_authenticated_approval
                        else "sticky_approval_required_or_mismatch"
                    ),
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                    status=ExecutionStatus.WAITING_APPROVAL,
                )

            if (
                self.dispatcher_policy.require_durable_idempotency_for_high_risk
                and risk.rank >= ExecutorRiskClass.HIGH.rank
                and not self.idempotency.durable
            ):
                return self._blocked(
                    request,
                    "durable_idempotency_required_for_high_risk",
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                )
            if (
                self.dispatcher_policy.require_distributed_idempotency_for_staging_and_production
                and request.environment in {"staging", "production"}
                and risk.rank >= ExecutorRiskClass.HIGH.rank
                and not self.idempotency.production_safe
            ):
                return self._blocked(
                    request,
                    "distributed_idempotency_required_for_high_risk",
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                )

            try:
                leases = self.credentials.acquire(request)
            except Exception as exc:
                return self._blocked(
                    request,
                    f"credential_lease_blocked:{type(exc).__name__}",
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                )

            # Audit is mandatory before any executor can run. Ledger failure raises and
            # therefore prevents execution.
            pre_ref = self.evidence.pre_audit(manifest)

            if request.idempotency_key:
                key = f"{request.tenant_id}:{request.skill_id}:{request.idempotency_key}"
                claimed, existing = await self.idempotency.claim(key, manifest.manifest_hash)
                if not claimed:
                    if existing and existing.manifest_hash != manifest.manifest_hash:
                        return self._blocked(
                            request,
                            "idempotency_key_manifest_conflict",
                            start=start,
                            manifest=manifest,
                            approval_fingerprint=approval_fingerprint,
                            risk=risk,
                        )
                    if (
                        existing
                        and existing.state is IdempotencyState.SUCCEEDED
                        and existing.result
                    ):
                        cached = dict(existing.result)
                        cached["policy_decision"] = "idempotent_replay"
                        return SkillExecutionResult(
                            execution_id=request.execution_id,
                            skill_id=request.skill_id,
                            status=ExecutionStatus.SUCCEEDED,
                            output=cached,
                            evidence_refs=[pre_ref],
                            manifest_hash=manifest.manifest_hash,
                            approval_fingerprint=approval_fingerprint,
                            risk_class=risk.value,
                            policy_decision="idempotent_replay",
                        )
                    return self._blocked(
                        request,
                        "idempotency_execution_in_progress_or_failed",
                        start=start,
                        manifest=manifest,
                        approval_fingerprint=approval_fingerprint,
                        risk=risk,
                    )
                idempotency_claimed = True

            executor = await self.executors.resolve(request)
            if executor is None:
                return self._blocked(
                    request,
                    "no_capable_executor",
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=risk,
                    evidence_refs=[pre_ref],
                )

            effective_risk = self.risk_classifier.classify(skill, executor.risk_class)
            if effective_risk.rank > risk.rank:
                # Any executor risk escalation invalidates the precomputed approval scope.
                return self._blocked(
                    request,
                    "executor_risk_escalation_requires_new_manifest_and_approval",
                    start=start,
                    manifest=manifest,
                    approval_fingerprint=approval_fingerprint,
                    risk=effective_risk,
                    evidence_refs=[pre_ref],
                )

            context = ExecutionContext(manifest=manifest, credentials=leases)
            try:
                result = await asyncio.wait_for(
                    executor.execute(request, context),
                    timeout=request.timeout_seconds,
                )
            except TimeoutError:
                result = SkillExecutionResult(
                    request.execution_id,
                    request.skill_id,
                    ExecutionStatus.TIMED_OUT,
                    error="executor_timeout",
                )
            except asyncio.CancelledError:
                result = SkillExecutionResult(
                    request.execution_id,
                    request.skill_id,
                    ExecutionStatus.CANCELLED,
                    error="execution_cancelled",
                )
                raise
            except Exception as exc:
                result = SkillExecutionResult(
                    request.execution_id,
                    request.skill_id,
                    ExecutionStatus.FAILED,
                    error=f"executor_error:{type(exc).__name__}",
                )

            result.duration_ms = int((time.monotonic() - start) * 1000)
            verification = self.verifier.verify(manifest, result)
            if not verification.valid:
                result = SkillExecutionResult(
                    request.execution_id,
                    request.skill_id,
                    ExecutionStatus.FAILED,
                    error=f"verification_failed:{verification.reason}",
                    duration_ms=result.duration_ms,
                )
            result.output = redact(result.output)
            result.error = redact(result.error)
            result.manifest_hash = manifest.manifest_hash
            result.approval_fingerprint = approval_fingerprint
            result.risk_class = risk.value
            final_ref = self.evidence.finalize(manifest, result)
            result.evidence_refs.extend([pre_ref, final_ref])

            if request.idempotency_key and idempotency_claimed:
                key = f"{request.tenant_id}:{request.skill_id}:{request.idempotency_key}"
                await self.idempotency.complete(
                    key,
                    success=result.status is ExecutionStatus.SUCCEEDED,
                    result={"status": result.status.value, "output": result.output},
                )
            return result
        except Exception as exc:
            # Control-plane errors are intentionally redacted and fail closed.
            return self._blocked(
                request,
                f"control_plane_failure:{type(exc).__name__}",
                start=start,
                manifest=manifest,
                approval_fingerprint=approval_fingerprint,
            )

    def _blocked(
        self,
        request: SkillExecutionRequest,
        reason: str,
        *,
        start: float,
        manifest: ImmutableExecutionManifest | None = None,
        approval_fingerprint: str | None = None,
        risk: ExecutorRiskClass | None = None,
        status: ExecutionStatus = ExecutionStatus.BLOCKED,
        evidence_refs: list[str] | None = None,
    ) -> SkillExecutionResult:
        return SkillExecutionResult(
            execution_id=request.execution_id,
            skill_id=request.skill_id,
            status=status,
            error=reason,
            duration_ms=int((time.monotonic() - start) * 1000),
            policy_decision="block",
            manifest_hash=manifest.manifest_hash if manifest else None,
            approval_fingerprint=approval_fingerprint,
            risk_class=risk.value if risk else None,
            evidence_refs=evidence_refs or [],
        )


def build_phase1_dispatcher(
    *,
    skill_registry: AgnesSkillRegistry,
    policy_engine: ExecutionPolicyEngine,
    approval_service: StickyApprovalResolver,
    ledger: AppendOnlyLedger,
    credential_broker: CredentialBroker | None,
) -> SkillExecutionDispatcher:
    return SkillExecutionDispatcher(
        skill_registry=skill_registry,
        policy_engine=policy_engine,
        approval_service=approval_service,
        ledger=ledger,
        credential_broker=credential_broker,
    )
