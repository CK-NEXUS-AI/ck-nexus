"""Evidence & Policy Engine — หลักฐาน + นโยบาย ทุกการกระทำ.

ทุก action ต้องมี:
1. Evidence — หลักฐานว่าทำจริง
2. Policy Check — ตรวจว่าอนุญาตไหม
3. Audit Trail — บันทึกว่าใครทำอะไรเมื่อไหร่

Core ไม่เคยเห็น API Key — ทำงานผ่าน Permission Gate + Vault ID เท่านั้น
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ActionType(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SECRET_ACCESS = "secret_access"
    DEPLOY = "deploy"


@dataclass
class PermissionRequest:
    """คำขอใช้สิทธิ์."""

    action: ActionType
    resource: str
    vault_id: str = ""
    context: str = ""
    requested_at: float = 0.0


@dataclass
class PermissionResult:
    """ผลตรวจสิทธิ์."""

    decision: PolicyDecision
    reason: str = ""
    granted_at: float = 0.0
    expires_at: float = 0.0


@dataclass
class AuditEntry:
    """บันทึกการกระทำ."""

    timestamp: float
    action: str
    actor: str
    resource: str
    decision: PolicyDecision
    evidence: str = ""
    vault_id: str = ""


class PolicyEngine:
    """Evidence & Policy Engine — ตรวจทุกการกระทำ.

    วิธีใช้:
        engine = PolicyEngine()

        # ขอใช้สิทธิ์
        result = engine.check_permission(ActionType.READ, "gmail")
        if result.decision == PolicyDecision.ALLOW:
            # ดำเนินการ
            engine.log_action("read_email", "user", "gmail", evidence="3 ฉบับ")

        # ดู audit trail
        trail = engine.get_audit_trail()
    """

    # นโยบาย default
    DEFAULT_POLICIES: dict[tuple[ActionType, str], PolicyDecision] = {
        (ActionType.READ, "gmail"): PolicyDecision.ALLOW,
        (ActionType.READ, "calendar"): PolicyDecision.ALLOW,
        (ActionType.READ, "sheets"): PolicyDecision.ALLOW,
        (ActionType.WRITE, "gmail"): PolicyDecision.REQUIRE_APPROVAL,
        (ActionType.WRITE, "sheets"): PolicyDecision.ALLOW,
        (ActionType.EXECUTE, "shell"): PolicyDecision.REQUIRE_APPROVAL,
        (ActionType.NETWORK, "api"): PolicyDecision.ALLOW,
        (ActionType.SECRET_ACCESS, "vault"): PolicyDecision.REQUIRE_APPROVAL,
        (ActionType.DEPLOY, "vercel"): PolicyDecision.REQUIRE_APPROVAL,
    }

    def __init__(self) -> None:
        self._policies: dict[tuple[ActionType, str], PolicyDecision] = dict(self.DEFAULT_POLICIES)
        self._audit: list[AuditEntry] = []
        self._granted_permissions: list[PermissionRequest] = []

    def check_permission(
        self,
        action: ActionType,
        resource: str,
        *,
        vault_id: str = "",
        context: str = "",
    ) -> PermissionResult:
        """ตรวจสิทธิ์ก่อนทำ action."""
        request = PermissionRequest(
            action=action,
            resource=resource,
            vault_id=vault_id,
            context=context,
            requested_at=time.time(),
        )

        decision = self._evaluate(request)
        result = PermissionResult(
            decision=decision,
            reason=self._get_reason(action, resource, decision),
            granted_at=time.time(),
        )

        if decision == PolicyDecision.ALLOW:
            self._granted_permissions.append(request)

        return result

    def log_action(
        self,
        action: str,
        actor: str,
        resource: str,
        *,
        evidence: str = "",
        decision: PolicyDecision = PolicyDecision.ALLOW,
        vault_id: str = "",
    ) -> None:
        """บันทึกการกระทำ + หลักฐาน."""
        entry = AuditEntry(
            timestamp=time.time(),
            action=action,
            actor=actor,
            resource=resource,
            decision=decision,
            evidence=evidence,
            vault_id=vault_id,
        )
        self._audit.append(entry)

    def get_audit_trail(
        self,
        *,
        actor: str | None = None,
        resource: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """ดูประวัติการกระทำ."""
        entries = self._audit
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if resource:
            entries = [e for e in entries if e.resource == resource]
        entries = entries[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "actor": e.actor,
                "resource": e.resource,
                "decision": e.decision.value,
                "evidence": e.evidence,
                "vault_id": e.vault_id,
            }
            for e in entries
        ]

    def add_policy(
        self,
        action: ActionType,
        resource: str,
        decision: PolicyDecision,
    ) -> None:
        """เพิ่มนโยบายใหม่."""
        self._policies[(action, resource)] = decision

    def stats(self) -> dict:
        """สถิติ."""
        allowed = sum(1 for e in self._audit if e.decision == PolicyDecision.ALLOW)
        denied = sum(1 for e in self._audit if e.decision == PolicyDecision.DENY)
        return {
            "total_actions": len(self._audit),
            "allowed": allowed,
            "denied": denied,
            "pending_approval": len(self._audit) - allowed - denied,
        }

    def _evaluate(self, request: PermissionRequest) -> PolicyDecision:
        """ตัดสินใจตามนโยบาย."""
        key = (request.action, request.resource)
        if key in self._policies:
            return self._policies[key]
        return PolicyDecision.REQUIRE_APPROVAL

    def _get_reason(
        self,
        action: ActionType,
        resource: str,
        decision: PolicyDecision,
    ) -> str:
        if decision == PolicyDecision.ALLOW:
            return f"Policy allows {action.value} on {resource}"
        if decision == PolicyDecision.DENY:
            return f"Policy denies {action.value} on {resource}"
        return f"No explicit policy for {action.value} on {resource} — requires approval"
