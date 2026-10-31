"""Fail-closed adapter for an independently operated OMNI authority.

This module deliberately does not mint identities, leases, or risk verdicts. The
configured authority must be a separate trust boundary and prove each issued
context, revocation state, and single-use execution binding.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .omni import OMNIExecutionContext, OmniGateError
from .request import SkillExecutionRequest, thaw


class OmniAuthorityUnavailable(PermissionError):
    """Raised when the independent OMNI authority cannot prove authorization."""


class DurableExecutionReplayStore:
    """Persistent single-use claims, atomic across processes and restarts."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("replay store must be persistent")
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.database_path, timeout=10) as db:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS consumed_executions (
                execution_id TEXT PRIMARY KEY, consumed_at REAL NOT NULL
            )""")
        with contextlib.suppress(OSError):
            Path(self.database_path).chmod(0o600)

    def consume_once(self, execution_id: str) -> bool:
        if not execution_id:
            return False
        db = sqlite3.connect(self.database_path, timeout=2, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=2000")
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute(
                    "INSERT INTO consumed_executions(execution_id, consumed_at) VALUES (?, ?)",
                    (execution_id, time.time()),
                )
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                return False
            db.execute("COMMIT")
            return True
        except sqlite3.Error:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()


class IndependentOmniAuthority(Protocol):
    def issue_context(self, request: SkillExecutionRequest) -> OMNIExecutionContext: ...

    def verify_context_proof(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool: ...

    def verify_evidence(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool: ...

    def is_lease_revoked(self, lease_id: str) -> bool: ...

    def consume_execution(self, execution_id: str, binding_sha256: str, lease_id: str) -> bool: ...


def execution_binding_sha256(request: SkillExecutionRequest, context: OMNIExecutionContext) -> str:
    """Hash the exact request and authority-issued context before single-use consume.

    The independent authority must atomically consume this execution ID only when
    the supplied digest matches the same signed authorization it issued. This
    binds replay protection to inputs, plan, actor/tenant, environment, policy,
    capability lease, risk verdict, and tool/target/runtime/verifier identity.
    """
    payload = {
        "request": {
            "execution_id": request.execution_id,
            "correlation_id": request.correlation_id,
            "skill_id": request.skill_id,
            "skill_version": request.skill_version,
            "executor": request.executor.value,
            "goal": request.goal,
            "plan_step": thaw(request.plan_step),
            "inputs": thaw(request.inputs),
            "tenant_id": request.tenant_id,
            "actor_id": request.actor_id,
            "environment": request.environment,
            "policy_version": request.policy_version,
            "workspace_id": request.workspace_id,
            "baseline_commit": request.baseline_commit,
            "requires_approval": request.requires_approval,
            "approval_id": request.approval_id,
            "timeout_seconds": request.timeout_seconds,
            "idempotency_key": request.idempotency_key,
            "allowlist_paths": list(request.allowlist_paths),
            "granted_capabilities": list(request.granted_capabilities),
            "credential_requirements": [
                {
                    "credential_id": item.credential_id,
                    "consumer": item.consumer,
                    "purpose": item.purpose,
                }
                for item in request.credential_requirements
            ],
        },
        "context": {
            "agent_id": context.identity.agent_id,
            "model_id": context.identity.model_id,
            "issuer": context.identity.issuer,
            "identity_ref": context.identity.identity_ref,
            "capability_id": context.capability_id,
            "lease": {
                "lease_id": context.lease.lease_id,
                "agent_id": context.lease.agent_id,
                "capabilities": list(context.lease.capabilities),
                "issued_at": context.lease.issued_at,
                "expires_at": context.lease.expires_at,
                "revocation_ref": context.lease.revocation_ref,
            },
            "policy_id": context.policy_id,
            "risk_verdict": {
                "risk_verdict_id": context.risk_verdict.risk_verdict_id,
                "execution_id": context.risk_verdict.execution_id,
                "agent_id": context.risk_verdict.agent_id,
                "capability_id": context.risk_verdict.capability_id,
                "policy_id": context.risk_verdict.policy_id,
                "decision": context.risk_verdict.decision.value,
                "risk": context.risk_verdict.risk.value,
                "blast_radius": context.risk_verdict.blast_radius,
                "reversibility": context.risk_verdict.reversibility,
                "data_sensitivity": context.risk_verdict.data_sensitivity,
                "external_side_effect": context.risk_verdict.external_side_effect,
            },
            "tool_id": context.tool_id,
            "target_id": context.target_id,
            "runtime_id": context.runtime_id,
            "verifier_id": context.verifier_id,
            "evidence_required": context.evidence_required,
            "intent_id": context.intent_id,
            "delegation": (
                {
                    "parent_execution_id": context.delegation.parent_execution_id,
                    "parent_agent_id": context.delegation.parent_agent_id,
                    "delegated_capabilities": list(context.delegation.delegated_capabilities),
                    "child_agent_id": context.delegation.child_agent_id,
                }
                if context.delegation is not None
                else None
            ),
        },
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


@dataclass(slots=True)
class OmniProviderAdapter:
    """Resolve OMNI context only through an independent, fail-closed authority.

    The authority object must be supplied by trusted server configuration. This
    adapter is not an issuer and intentionally has no local/test fallback.
    """

    authority: IndependentOmniAuthority | None = None
    replay_store: DurableExecutionReplayStore | None = None

    def __call__(self, request: SkillExecutionRequest) -> OMNIExecutionContext:
        authority = self.authority
        if authority is None:
            raise OmniAuthorityUnavailable("omni_authority_not_configured")
        if self.replay_store is None:
            raise OmniAuthorityUnavailable("durable_replay_store_not_configured")
        if not request.execution_id:
            raise OmniGateError("execution_id_missing")
        declared_tool = request.plan_step.get("tool_id")
        declared_target = request.plan_step.get("target_id")
        if not isinstance(declared_tool, str) or not declared_tool:
            raise OmniGateError("tool_binding_missing_from_request")
        if not isinstance(declared_target, str) or not declared_target:
            raise OmniGateError("target_binding_missing_from_request")

        try:
            context = authority.issue_context(request)
            if not isinstance(context, OMNIExecutionContext):
                raise OmniAuthorityUnavailable("authority_returned_invalid_context")
            if not authority.verify_context_proof(request, context):
                raise OmniAuthorityUnavailable("authority_proof_invalid")
            context.validate(request)
            if context.evidence_required and not authority.verify_evidence(request, context):
                raise OmniAuthorityUnavailable("execution_evidence_invalid_or_missing")
            if context.tool_id != declared_tool or context.target_id != declared_target:
                raise OmniGateError("execution_tool_target_binding_mismatch")
            if authority.is_lease_revoked(context.lease.lease_id):
                raise OmniGateError("capability_lease_revoked")
            binding_sha256 = execution_binding_sha256(request, context)
            # The authority must atomically consume the ID and this exact binding.
            # Recheck revocation immediately before consume to narrow the revoke race.
            if authority.is_lease_revoked(context.lease.lease_id):
                raise OmniGateError("capability_lease_revoked")
            # Authority must atomically check lease revocation and consume the binding.
            if not authority.consume_execution(
                request.execution_id, binding_sha256, context.lease.lease_id
            ):
                raise OmniAuthorityUnavailable("execution_grant_replayed_or_unavailable")
            if not self.replay_store.consume_once(request.execution_id):
                raise OmniAuthorityUnavailable("execution_grant_replayed_locally")
            return context
        except (OmniGateError, OmniAuthorityUnavailable):
            raise
        except Exception as exc:
            # Network, decoding, and provider failures must never become permission.
            raise OmniAuthorityUnavailable("omni_authority_validation_failed") from exc
