"""AuthZEN Authorization API 1.0 interoperability adapter.

This module is a Policy Enforcement Point (PEP)-side adapter only. External PDP
responses are untrusted authorization inputs and never replace CK-NEXUS Governor
authority, human approval, independent verification, or Production gates.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .governor import (
    ActionProposal,
    CognitiveGovernor,
    GovernanceResult,
    GovernorDecision,
)

AUTHZEN_SPEC_VERSION = "1.0"
AUTHZEN_ACCESS_EVALUATION_PATH = "/access/v1/evaluation"
_ALLOWED_REQUEST_KEYS = frozenset({"subject", "action", "resource", "context"})
_ALLOWED_RESPONSE_KEYS = frozenset({"decision", "context"})


@dataclass(frozen=True, slots=True)
class AuthZENEnforcementResult:
    """Combined external-PDP and CK-NEXUS Governor decision projection."""

    pdp_decision: bool
    governor_result: GovernanceResult
    allowed: bool
    reason: str
    evidence_digest: str
    authority: str = "CK-NEXUS"
    spec_version: str = AUTHZEN_SPEC_VERSION


class AuthZENAdapter:
    """Validate AuthZEN objects and enforce them through the CK Governor.

    The adapter performs no HTTP calls, credential access, policy storage, tool
    execution, external writes, or Production mutation.
    """

    def __init__(self, governor: CognitiveGovernor | None = None) -> None:
        self._governor = governor or CognitiveGovernor()

    def enforce(
        self,
        request: Mapping[str, Any],
        response: Mapping[str, Any],
        proposal: ActionProposal,
    ) -> AuthZENEnforcementResult:
        normalized_request = self._validate_request(request)
        normalized_response = self._validate_response(response)
        self._validate_binding(normalized_request, proposal)

        pdp_decision = normalized_response["decision"]
        governor_result = self._governor.decide(proposal)
        allowed = pdp_decision and governor_result.decision is GovernorDecision.ALLOW

        if not pdp_decision:
            reason = "external_pdp_denied"
        elif governor_result.decision is GovernorDecision.ALLOW:
            reason = "external_pdp_and_ck_governor_allow"
        elif governor_result.decision is GovernorDecision.REQUIRE_APPROVAL:
            reason = "ck_governor_requires_approval"
        else:
            reason = "ck_governor_denied"

        digest = self._digest(
            request=normalized_request,
            response=normalized_response,
            proposal=proposal,
            governor_result=governor_result,
            allowed=allowed,
            reason=reason,
        )
        return AuthZENEnforcementResult(
            pdp_decision=pdp_decision,
            governor_result=governor_result,
            allowed=allowed,
            reason=reason,
            evidence_digest=digest,
        )

    @staticmethod
    def _validate_request(request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise ValueError("AuthZEN request must be an object")
        unknown = set(request) - _ALLOWED_REQUEST_KEYS
        if unknown:
            raise ValueError(f"unsupported AuthZEN request keys: {sorted(unknown)}")

        subject = AuthZENAdapter._entity(request.get("subject"), "subject", needs_id=True)
        resource = AuthZENAdapter._entity(request.get("resource"), "resource", needs_id=True)
        action = AuthZENAdapter._action(request.get("action"))

        normalized: dict[str, Any] = {
            "subject": subject,
            "action": action,
            "resource": resource,
        }
        if "context" in request:
            context = request["context"]
            if not isinstance(context, Mapping):
                raise ValueError("AuthZEN context must be an object")
            normalized["context"] = dict(context)
        return normalized

    @staticmethod
    def _validate_response(response: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(response, Mapping):
            raise ValueError("AuthZEN response must be an object")
        unknown = set(response) - _ALLOWED_RESPONSE_KEYS
        if unknown:
            raise ValueError(f"unsupported AuthZEN response keys: {sorted(unknown)}")
        decision = response.get("decision")
        if type(decision) is not bool:
            raise ValueError("AuthZEN response decision must be boolean")

        normalized: dict[str, Any] = {"decision": decision}
        if "context" in response:
            context = response["context"]
            if not isinstance(context, Mapping):
                raise ValueError("AuthZEN response context must be an object")
            normalized["context"] = dict(context)
        return normalized

    @staticmethod
    def _entity(value: Any, name: str, *, needs_id: bool) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError(f"AuthZEN {name} must be an object")
        allowed = {"type", "id", "properties"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unsupported AuthZEN {name} keys: {sorted(unknown)}")

        entity_type = value.get("type")
        if not isinstance(entity_type, str) or not entity_type.strip():
            raise ValueError(f"AuthZEN {name}.type must be a non-empty string")
        entity_id = value.get("id")
        if needs_id and (not isinstance(entity_id, str) or not entity_id.strip()):
            raise ValueError(f"AuthZEN {name}.id must be a non-empty string")

        normalized: dict[str, Any] = {"type": entity_type}
        if entity_id is not None:
            if not isinstance(entity_id, str) or not entity_id.strip():
                raise ValueError(f"AuthZEN {name}.id must be a non-empty string")
            normalized["id"] = entity_id
        if "properties" in value:
            properties = value["properties"]
            if not isinstance(properties, Mapping):
                raise ValueError(f"AuthZEN {name}.properties must be an object")
            normalized["properties"] = dict(properties)
        return normalized

    @staticmethod
    def _action(value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError("AuthZEN action must be an object")
        allowed = {"name", "properties"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unsupported AuthZEN action keys: {sorted(unknown)}")

        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("AuthZEN action.name must be a non-empty string")
        normalized: dict[str, Any] = {"name": name}
        if "properties" in value:
            properties = value["properties"]
            if not isinstance(properties, Mapping):
                raise ValueError("AuthZEN action.properties must be an object")
            normalized["properties"] = dict(properties)
        return normalized

    @staticmethod
    def _validate_binding(request: Mapping[str, Any], proposal: ActionProposal) -> None:
        subject = request["subject"]
        action = request["action"]
        resource = request["resource"]
        expected_scope = f"{resource['type']}:{resource['id']}"
        if proposal.actor != subject["id"]:
            raise ValueError("AuthZEN subject is not bound to CK proposal actor")
        if proposal.action != action["name"]:
            raise ValueError("AuthZEN action is not bound to CK proposal action")
        if proposal.scope != expected_scope:
            raise ValueError("AuthZEN resource is not bound to CK proposal scope")

    @staticmethod
    def _digest(
        *,
        request: Mapping[str, Any],
        response: Mapping[str, Any],
        proposal: ActionProposal,
        governor_result: GovernanceResult,
        allowed: bool,
        reason: str,
    ) -> str:
        payload = {
            "authzen_spec_version": AUTHZEN_SPEC_VERSION,
            "request": request,
            "response": response,
            "proposal": {
                "action": proposal.action,
                "actor": proposal.actor,
                "scope": proposal.scope,
                "risk": proposal.risk.value,
                "external_write": proposal.external_write,
                "destructive": proposal.destructive,
                "production_mutation": proposal.production_mutation,
                "verified": proposal.verified,
                "human_approved": proposal.human_approved,
                "evidence_refs": proposal.evidence_refs,
            },
            "governor": {
                "decision": governor_result.decision.value,
                "reasons": governor_result.reasons,
                "requires_verification": governor_result.requires_verification,
                "requires_human_approval": governor_result.requires_human_approval,
            },
            "allowed": allowed,
            "reason": reason,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
