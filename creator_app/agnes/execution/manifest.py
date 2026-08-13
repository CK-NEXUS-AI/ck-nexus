from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .request import ExecutorRiskClass, SkillExecutionRequest, canonical_json


@dataclass(frozen=True, slots=True)
class ImmutableExecutionManifest:
    execution_id: str
    correlation_id: str
    tenant_id: str
    actor_id: str
    environment: str
    skill_id: str
    skill_version: str
    executor: str
    executor_risk_class: str
    goal_hash: str
    input_hash: str
    plan_hash: str
    workspace_id: str | None
    baseline_commit: str | None
    policy_version: str
    approval_fingerprint: str
    idempotency_key: str | None
    allowlist_paths: tuple[str, ...]
    permissions_hash: str
    credential_requirements_hash: str
    manifest_hash: str

    @classmethod
    def freeze(
        cls,
        request: SkillExecutionRequest,
        *,
        risk_class: ExecutorRiskClass,
        approval_fingerprint: str,
    ) -> ImmutableExecutionManifest:
        goal_hash = _sha(request.goal)
        input_hash = _sha(canonical_json(request.inputs))
        plan_hash = _sha(canonical_json(request.plan_step))
        credentials_payload = [
            {
                "credential_id": item.credential_id,
                "consumer": item.consumer,
                "purpose": item.purpose,
            }
            for item in request.credential_requirements
        ]
        permissions_hash = _sha(json.dumps(list(request.granted_capabilities), separators=(",", ":")))
        credential_requirements_hash = _sha(
            json.dumps(credentials_payload, sort_keys=True, separators=(",", ":"))
        )
        payload = {
            "execution_id": request.execution_id,
            "correlation_id": request.correlation_id,
            "tenant_id": request.tenant_id,
            "actor_id": request.actor_id,
            "environment": request.environment,
            "skill_id": request.skill_id,
            "skill_version": request.skill_version,
            "executor": request.executor.value,
            "executor_risk_class": risk_class.value,
            "goal_hash": goal_hash,
            "input_hash": input_hash,
            "plan_hash": plan_hash,
            "workspace_id": request.workspace_id,
            "baseline_commit": request.baseline_commit,
            "policy_version": request.policy_version,
            "approval_fingerprint": approval_fingerprint,
            "idempotency_key": request.idempotency_key,
            "allowlist_paths": list(request.allowlist_paths),
            "permissions_hash": permissions_hash,
            "credential_requirements_hash": credential_requirements_hash,
        }
        manifest_hash = _sha(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        payload["allowlist_paths"] = tuple(payload["allowlist_paths"])
        return cls(**payload, manifest_hash=manifest_hash)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
