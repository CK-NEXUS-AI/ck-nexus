from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from time import time

from .request import ExecutorRiskClass, SkillExecutionRequest, canonical_json


@dataclass(frozen=True, slots=True)
class ApprovalGrant:
    approval_id: str
    fingerprint: str
    approved_by: str
    expires_at: float
    authenticated: bool = False
    actor_id: str | None = None
    authn_method: str | None = None


class StickyApprovalResolver:
    """Approval is bound to immutable execution facts, not merely an approval id."""

    def __init__(self) -> None:
        self._grants: dict[str, ApprovalGrant] = {}

    @staticmethod
    def fingerprint(request: SkillExecutionRequest, risk_class: ExecutorRiskClass) -> str:
        payload = {
            "skill_id": request.skill_id,
            "skill_version": request.skill_version,
            "input_hash": hashlib.sha256(canonical_json(request.inputs).encode()).hexdigest(),
            "actor_id": request.actor_id,
            "tenant_id": request.tenant_id,
            "workspace_id": request.workspace_id,
            "baseline_commit": request.baseline_commit,
            "policy_version": request.policy_version,
            "executor": request.executor.value,
            "risk_class": risk_class.value,
            "granted_capabilities": list(request.granted_capabilities),
            "allowlist_paths": list(request.allowlist_paths),
            "credential_requirements": [
                {
                    "credential_id": item.credential_id,
                    "consumer": item.consumer,
                    "purpose": item.purpose,
                }
                for item in request.credential_requirements
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def grant(
        self,
        *,
        approval_id: str,
        fingerprint: str,
        approved_by: str,
        ttl_seconds: int = 900,
    ) -> ApprovalGrant:
        if ttl_seconds <= 0:
            raise ValueError("approval ttl must be positive")
        grant = ApprovalGrant(
            approval_id=approval_id,
            fingerprint=fingerprint,
            approved_by=approved_by,
            expires_at=time() + ttl_seconds,
            authenticated=False,
        )
        self._grants[approval_id] = grant
        return grant


    def grant_verified(
        self,
        *,
        approval_id: str,
        fingerprint: str,
        actor_id: str,
        expires_at: float,
        authn_method: str,
    ) -> ApprovalGrant:
        if expires_at <= time():
            raise ValueError("verified approval must not already be expired")
        if not all(v.strip() for v in (approval_id, fingerprint, actor_id, authn_method)):
            raise ValueError("verified approval fields cannot be empty")
        grant = ApprovalGrant(
            approval_id=approval_id.strip(),
            fingerprint=fingerprint.strip(),
            approved_by=actor_id.strip(),
            expires_at=expires_at,
            authenticated=True,
            actor_id=actor_id.strip(),
            authn_method=authn_method.strip(),
        )
        self._grants[grant.approval_id] = grant
        return grant

    def find_matching(
        self, fingerprint: str, *, require_authenticated: bool = False
    ) -> ApprovalGrant | None:
        now = time()
        for grant in self._grants.values():
            if (
                grant.expires_at > now
                and (grant.authenticated or not require_authenticated)
                and hmac.compare_digest(grant.fingerprint, fingerprint)
            ):
                return grant
        return None

    def is_approved(
        self, *, approval_id: str | None, fingerprint: str, require_authenticated: bool = False
    ) -> bool:
        if not approval_id:
            return False
        grant = self._grants.get(approval_id)
        if grant is None or grant.expires_at <= time():
            return False
        if require_authenticated and not grant.authenticated:
            return False
        return hmac.compare_digest(grant.fingerprint, fingerprint)
