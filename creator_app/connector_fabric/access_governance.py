from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from creator_app.privacy_firewall.contracts import DataClassification, TrustLevel


class ExternalAccessClass(StrEnum):
    """How CK-NEXUS is allowed to reach a data source."""

    PUBLIC_WEB = "public_web"
    AUTHORIZED_CONNECTED = "authorized_connected"
    PRIVATE_UNAUTHORIZED = "private_unauthorized"
    PROHIBITED_BYPASS = "prohibited_bypass"


class ExternalAction(StrEnum):
    SEARCH = "search"
    READ = "read"
    INGEST = "ingest"
    STORE = "store"
    WRITE = "write"
    SEND = "send"
    DELETE = "delete"
    TRAIN = "train"
    CREDENTIAL_REQUEST = "credential_request"


class AccessOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    QUARANTINE = "quarantine"


_READ_ACTIONS = frozenset({ExternalAction.SEARCH, ExternalAction.READ, ExternalAction.INGEST})
_MUTATING_ACTIONS = frozenset(
    {ExternalAction.STORE, ExternalAction.WRITE, ExternalAction.SEND, ExternalAction.DELETE}
)
_EGRESS_ACTIONS = frozenset({ExternalAction.WRITE, ExternalAction.SEND})


@dataclass(frozen=True, slots=True)
class ExternalAccessRequest:
    request_id: str
    source: str
    access_class: ExternalAccessClass
    action: ExternalAction
    purpose: str
    user_authorized: bool = False
    connector_authorized: bool = False
    required_scopes: frozenset[str] = field(default_factory=frozenset)
    granted_scopes: frozenset[str] = field(default_factory=frozenset)
    consent_ref: str | None = None
    consent_active: bool = False
    approval_ref: str | None = None
    privacy_decision_ref: str | None = None
    retention_ref: str | None = None
    classification: DataClassification = DataClassification.PUBLIC
    trust: TrustLevel = TrustLevel.UNTRUSTED
    content_digest: str | None = None
    bypass_requested: bool = False

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.purpose.strip():
            raise ValueError("purpose must not be empty")


@dataclass(frozen=True, slots=True)
class ExternalAccessDecision:
    outcome: AccessOutcome
    allowed: bool
    reason: str
    evidence: dict[str, object]


class ExternalAccessGovernor:
    """Deterministic, fail-closed governor for external data access.

    The governor has no network or credential capability. It decides whether a
    separately governed browser, connector, MCP tool, or API adapter may act.
    """

    def evaluate(self, request: ExternalAccessRequest) -> ExternalAccessDecision:
        outcome, reason = self._decide(request)
        evidence = self._evidence(request, outcome=outcome, reason=reason)
        return ExternalAccessDecision(
            outcome=outcome,
            allowed=outcome is AccessOutcome.ALLOW,
            reason=reason,
            evidence=evidence,
        )

    def _decide(self, request: ExternalAccessRequest) -> tuple[AccessOutcome, str]:
        if request.bypass_requested or request.access_class is ExternalAccessClass.PROHIBITED_BYPASS:
            return AccessOutcome.DENY, "authentication_or_access_control_bypass_forbidden"
        if request.action is ExternalAction.CREDENTIAL_REQUEST:
            return AccessOutcome.DENY, "raw_credentials_must_not_be_requested"
        if request.action is ExternalAction.TRAIN:
            return AccessOutcome.DENY, "external_or_personal_data_training_requires_separate_policy"
        if request.access_class is ExternalAccessClass.PRIVATE_UNAUTHORIZED:
            return AccessOutcome.DENY, "private_source_has_no_authorized_connection"
        if not request.user_authorized:
            return AccessOutcome.DENY, "user_authorization_required"

        if request.access_class is ExternalAccessClass.PUBLIC_WEB:
            if request.action in _READ_ACTIONS:
                if request.action is ExternalAction.INGEST and request.trust is TrustLevel.UNTRUSTED:
                    return AccessOutcome.QUARANTINE, "untrusted_external_content_requires_verification"
                return AccessOutcome.ALLOW, "bounded_public_read_authorized"
            return AccessOutcome.DENY, "public_source_mutation_requires_governed_connector"

        if request.access_class is not ExternalAccessClass.AUTHORIZED_CONNECTED:
            return AccessOutcome.DENY, "unknown_access_class"
        if not request.connector_authorized:
            return AccessOutcome.DENY, "connected_source_authorization_required"
        if not request.consent_ref or not request.consent_active:
            return AccessOutcome.DENY, "active_consent_reference_required"
        if not request.required_scopes.issubset(request.granted_scopes):
            return AccessOutcome.DENY, "connector_scope_insufficient"

        if request.action in _READ_ACTIONS:
            if request.action is ExternalAction.INGEST and request.trust is TrustLevel.UNTRUSTED:
                return AccessOutcome.QUARANTINE, "untrusted_connected_content_requires_verification"
            return AccessOutcome.ALLOW, "authorized_connected_read"

        if request.action in _MUTATING_ACTIONS:
            if not request.approval_ref:
                return AccessOutcome.DENY, "explicit_mutation_approval_required"
            if request.action is ExternalAction.STORE and not request.retention_ref:
                return AccessOutcome.DENY, "retention_policy_reference_required"
            if (
                request.action in _EGRESS_ACTIONS
                and request.classification is not DataClassification.PUBLIC
                and not request.privacy_decision_ref
            ):
                return AccessOutcome.DENY, "privacy_disclosure_decision_required"
            return AccessOutcome.ALLOW, "authorized_connected_mutation_with_approval"
        return AccessOutcome.DENY, "action_not_authorized"

    @staticmethod
    def _evidence(
        request: ExternalAccessRequest,
        *,
        outcome: AccessOutcome,
        reason: str,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "cknexus.external-access-decision.v1",
            "request_id": request.request_id,
            "source": request.source,
            "access_class": request.access_class.value,
            "action": request.action.value,
            "purpose": request.purpose,
            "classification": request.classification.value,
            "trust": request.trust.value,
            "user_authorized": request.user_authorized,
            "connector_authorized": request.connector_authorized,
            "required_scopes": sorted(request.required_scopes),
            "granted_scope_count": len(request.granted_scopes),
            "consent_ref": request.consent_ref,
            "consent_active": request.consent_active,
            "approval_ref": request.approval_ref,
            "privacy_decision_ref": request.privacy_decision_ref,
            "retention_ref": request.retention_ref,
            "content_digest": request.content_digest,
            "outcome": outcome.value,
            "reason": reason,
            "authority": "CK-NEXUS",
            "raw_credentials_persisted": False,
            "raw_content_persisted": False,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {**payload, "decision_digest": hashlib.sha256(encoded).hexdigest()}


def content_sha256(content: str) -> str:
    """Create a provenance digest without retaining the source content itself."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IngestionAssessment:
    outcome: AccessOutcome
    reason: str
    taints: frozenset[str]
    content_digest: str
    assessed_at: str


_INSTRUCTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "developer message",
    "execute this tool",
    "call this tool",
    "reveal secrets",
    "send credentials",
)


def assess_external_content(content: str, *, trust: TrustLevel) -> IngestionAssessment:
    """Treat retrieved content as data, never as execution authority."""
    digest = content_sha256(content)
    lowered = content.lower()
    taints = {"external-content"}
    if any(marker in lowered for marker in _INSTRUCTION_MARKERS):
        taints.add("possible-prompt-injection")
    if trust is TrustLevel.UNTRUSTED:
        return IngestionAssessment(
            outcome=AccessOutcome.QUARANTINE,
            reason="untrusted_content_requires_verification",
            taints=frozenset(taints),
            content_digest=digest,
            assessed_at=datetime.now(UTC).isoformat(),
        )
    return IngestionAssessment(
        outcome=AccessOutcome.ALLOW,
        reason="trusted_content_may_enter_processing_pipeline",
        taints=frozenset(taints),
        content_digest=digest,
        assessed_at=datetime.now(UTC).isoformat(),
    )
