"""Fail-closed A2A v1.0 Agent Card admission for CK-NEXUS.

This module validates already-retrieved Agent Cards. It performs no network calls,
credential handling, message sending, task execution, or Production mutation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse

from creator_app.connector_fabric.access_governance import (
    AccessOutcome,
    ExternalAccessClass,
    ExternalAccessDecision,
    ExternalAccessGovernor,
    ExternalAccessRequest,
    ExternalAction,
)

A2A_RELEASE_VERSION = "1.0.0"
A2A_PROTOCOL_VERSION = "1.0"
A2A_AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent-card.json"
_CORE_BINDINGS = frozenset({"JSONRPC", "GRPC", "HTTP+JSON"})
_CARD_FIELDS = frozenset(
    {
        "name",
        "description",
        "supportedInterfaces",
        "provider",
        "version",
        "documentationUrl",
        "capabilities",
        "securitySchemes",
        "securityRequirements",
        "defaultInputModes",
        "defaultOutputModes",
        "skills",
        "signatures",
        "iconUrl",
    }
)
_SKILL_FIELDS = frozenset(
    {
        "id",
        "name",
        "description",
        "tags",
        "examples",
        "inputModes",
        "outputModes",
        "securityRequirements",
    }
)


class A2AAdmissionStatus(StrEnum):
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    DISCOVERED_CANDIDATE = "DISCOVERED_CANDIDATE"


class AgentCardSignatureVerifier(Protocol):
    """Trusted RFC 8785/JWS verifier boundary supplied by CK Verification."""

    def verify(
        self,
        *,
        unsigned_card: Mapping[str, object],
        signatures: tuple[dict[str, object], ...],
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class A2AAdmissionResult:
    status: A2AAdmissionStatus
    discovered: bool
    admitted_candidate: bool
    execution_allowed: bool
    reason: str
    agent_name: str | None
    agent_version: str | None
    skill_ids: tuple[str, ...]
    interface_bindings: tuple[str, ...]
    signature_state: str
    card_digest: str
    access_decision: ExternalAccessDecision
    authority: str = "CK-NEXUS"
    production_mutation_allowed: bool = False
    verification_upgrade_allowed: bool = False


@dataclass(frozen=True, slots=True)
class _ValidatedCard:
    normalized: dict[str, object]
    unsigned_card: dict[str, object]
    signatures: tuple[dict[str, object], ...]


class A2AAgentCardAdmission:
    """Admit A2A Agent Cards as non-executable discovery candidates only."""

    def __init__(
        self,
        access_governor: ExternalAccessGovernor | None = None,
        signature_verifier: AgentCardSignatureVerifier | None = None,
    ) -> None:
        self._access_governor = access_governor or ExternalAccessGovernor()
        self._signature_verifier = signature_verifier

    def evaluate(
        self,
        card: Mapping[str, object],
        *,
        expected_host: str,
        user_authorized: bool,
    ) -> A2AAdmissionResult:
        host = expected_host.strip().lower()
        if not host:
            raise ValueError("expected_host must not be empty")

        access = self._external_access(card, expected_host=host, user_authorized=user_authorized)
        if access.outcome is not AccessOutcome.ALLOW:
            return self._result(
                status=A2AAdmissionStatus.REJECTED,
                reason=f"external_access_denied:{access.reason}",
                access=access,
            )

        try:
            validated = self._validate_card(card, expected_host=host)
        except (TypeError, ValueError) as exc:
            return self._result(
                status=A2AAdmissionStatus.REJECTED,
                reason=f"invalid_agent_card:{exc}",
                access=access,
            )

        signature_state = "ABSENT"
        if validated.signatures:
            signature_state, terminal = self._verify_signatures(validated, access)
            if terminal is not None:
                return terminal

        required_extensions = validated.normalized["required_extensions"]
        if required_extensions:
            return self._result(
                status=A2AAdmissionStatus.QUARANTINED,
                reason="required_a2a_extension_requires_explicit_ck_admission",
                access=access,
                normalized=validated.normalized,
                signature_state=signature_state,
            )

        return self._result(
            status=A2AAdmissionStatus.DISCOVERED_CANDIDATE,
            reason="agent_card_valid_for_non_executable_discovery",
            access=access,
            normalized=validated.normalized,
            signature_state=signature_state,
        )

    def _verify_signatures(
        self,
        validated: _ValidatedCard,
        access: ExternalAccessDecision,
    ) -> tuple[str, A2AAdmissionResult | None]:
        if self._signature_verifier is None:
            result = self._result(
                status=A2AAdmissionStatus.QUARANTINED,
                reason="agent_card_signature_present_but_no_trusted_verifier",
                access=access,
                normalized=validated.normalized,
                signature_state="UNVERIFIED",
            )
            return "UNVERIFIED", result
        try:
            valid = self._signature_verifier.verify(
                unsigned_card=validated.unsigned_card,
                signatures=validated.signatures,
            )
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            result = self._result(
                status=A2AAdmissionStatus.REJECTED,
                reason="agent_card_signature_verification_failed",
                access=access,
                normalized=validated.normalized,
                signature_state="FAILED",
            )
            return "FAILED", result
        return "VERIFIED_BY_TRUSTED_BOUNDARY", None

    def _external_access(
        self,
        card: Mapping[str, object],
        *,
        expected_host: str,
        user_authorized: bool,
    ) -> ExternalAccessDecision:
        request = ExternalAccessRequest(
            request_id=self._request_id(card),
            source=f"https://{expected_host}{A2A_AGENT_CARD_WELL_KNOWN_PATH}",
            access_class=ExternalAccessClass.PUBLIC_WEB,
            action=ExternalAction.READ,
            purpose="a2a-agent-card-discovery",
            user_authorized=user_authorized,
        )
        return self._access_governor.evaluate(request)

    @staticmethod
    def _validate_card(
        card: Mapping[str, object],
        *,
        expected_host: str,
    ) -> _ValidatedCard:
        if not isinstance(card, Mapping):
            raise TypeError("Agent Card must be an object")
        unknown = set(card) - _CARD_FIELDS
        if unknown:
            raise ValueError(f"unsupported Agent Card fields: {sorted(unknown)}")

        interfaces, bindings = A2AAgentCardAdmission._interfaces(
            card.get("supportedInterfaces"),
            expected_host=expected_host,
        )
        skills, skill_ids = A2AAgentCardAdmission._skills(card.get("skills"))
        capabilities, required_extensions = A2AAgentCardAdmission._capabilities(
            card.get("capabilities")
        )
        signatures = A2AAgentCardAdmission._signatures(card.get("signatures"))

        normalized: dict[str, object] = {
            "name": A2AAgentCardAdmission._required_string(card, "name"),
            "description": A2AAgentCardAdmission._required_string(card, "description"),
            "supportedInterfaces": interfaces,
            "version": A2AAgentCardAdmission._required_string(card, "version"),
            "capabilities": capabilities,
            "defaultInputModes": A2AAgentCardAdmission._string_list(
                card.get("defaultInputModes"),
                "defaultInputModes",
            ),
            "defaultOutputModes": A2AAgentCardAdmission._string_list(
                card.get("defaultOutputModes"),
                "defaultOutputModes",
            ),
            "skills": skills,
            "skill_ids": skill_ids,
            "interface_bindings": bindings,
            "required_extensions": required_extensions,
        }
        for optional in (
            "provider",
            "documentationUrl",
            "securitySchemes",
            "securityRequirements",
            "iconUrl",
        ):
            if optional in card:
                normalized[optional] = card[optional]

        unsigned_card = dict(card)
        unsigned_card.pop("signatures", None)
        json.dumps(unsigned_card, ensure_ascii=False, sort_keys=True)
        return _ValidatedCard(
            normalized=normalized,
            unsigned_card=unsigned_card,
            signatures=signatures,
        )

    @staticmethod
    def _interfaces(
        value: object,
        *,
        expected_host: str,
    ) -> tuple[tuple[dict[str, str], ...], tuple[str, ...]]:
        if not isinstance(value, list) or not value:
            raise ValueError("supportedInterfaces must be a non-empty list")
        normalized: list[dict[str, str]] = []
        bindings: list[str] = []
        for raw in value:
            if not isinstance(raw, Mapping):
                raise ValueError("AgentInterface must be an object")
            allowed = {"url", "protocolBinding", "tenant", "protocolVersion"}
            unknown = set(raw) - allowed
            if unknown:
                raise ValueError(f"unsupported AgentInterface fields: {sorted(unknown)}")
            url = A2AAgentCardAdmission._required_string(raw, "url")
            binding = A2AAgentCardAdmission._required_string(raw, "protocolBinding")
            protocol_version = A2AAgentCardAdmission._required_string(raw, "protocolVersion")
            if protocol_version != A2A_PROTOCOL_VERSION:
                raise ValueError("AgentInterface protocolVersion must be 1.0")
            if binding not in _CORE_BINDINGS:
                raise ValueError("custom A2A protocol binding requires explicit CK admission")
            A2AAgentCardAdmission._validate_interface_url(
                url,
                binding=binding,
                expected_host=expected_host,
            )
            item = {
                "url": url,
                "protocolBinding": binding,
                "protocolVersion": protocol_version,
            }
            tenant = raw.get("tenant")
            if tenant is not None:
                if not isinstance(tenant, str) or not tenant.strip():
                    raise ValueError("AgentInterface tenant must be a non-empty string")
                item["tenant"] = tenant
            normalized.append(item)
            bindings.append(binding)
        return tuple(normalized), tuple(bindings)

    @staticmethod
    def _validate_interface_url(url: str, *, binding: str, expected_host: str) -> None:
        if binding == "GRPC":
            if "://" in url:
                raise ValueError("GRPC interface must use host:port form")
            try:
                host, port_text = url.rsplit(":", 1)
                port = int(port_text)
            except (TypeError, ValueError):
                raise ValueError("GRPC interface must use valid host:port") from None
            if host.lower() != expected_host or not 1 <= port <= 65535:
                raise ValueError("GRPC interface host/port is outside admitted origin")
            return

        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("HTTP-based A2A interface must use absolute HTTPS")
        if parsed.hostname.lower() != expected_host:
            raise ValueError("A2A interface host is outside admitted origin")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("A2A interface URL contains forbidden authority/fragment data")

    @staticmethod
    def _skills(value: object) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
        if not isinstance(value, list) or not value:
            raise ValueError("skills must be a non-empty list")
        normalized: list[dict[str, object]] = []
        seen: set[str] = set()
        for raw in value:
            if not isinstance(raw, Mapping):
                raise ValueError("AgentSkill must be an object")
            unknown = set(raw) - _SKILL_FIELDS
            if unknown:
                raise ValueError(f"unsupported AgentSkill fields: {sorted(unknown)}")
            required = {"id", "name", "description", "tags"}
            if not required.issubset(raw):
                raise ValueError("AgentSkill requires id/name/description/tags")
            skill_id = A2AAgentCardAdmission._required_string(raw, "id")
            if skill_id in seen:
                raise ValueError("AgentSkill id must be unique")
            seen.add(skill_id)
            item: dict[str, object] = {
                "id": skill_id,
                "name": A2AAgentCardAdmission._required_string(raw, "name"),
                "description": A2AAgentCardAdmission._required_string(raw, "description"),
                "tags": A2AAgentCardAdmission._string_list(raw.get("tags"), "tags"),
            }
            for optional in ("examples", "inputModes", "outputModes", "securityRequirements"):
                if optional in raw:
                    item[optional] = raw[optional]
            normalized.append(item)
        return tuple(normalized), tuple(sorted(seen))

    @staticmethod
    def _capabilities(value: object) -> tuple[dict[str, object], tuple[str, ...]]:
        if not isinstance(value, Mapping):
            raise ValueError("capabilities must be an object")
        allowed = {"streaming", "pushNotifications", "extensions", "extendedAgentCard"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unsupported capabilities fields: {sorted(unknown)}")
        normalized = dict(value)
        extensions = value.get("extensions", [])
        if not isinstance(extensions, list):
            raise ValueError("capabilities.extensions must be a list")
        required_extensions: list[str] = []
        for extension in extensions:
            if not isinstance(extension, Mapping):
                raise ValueError("AgentExtension must be an object")
            uri = extension.get("uri")
            required = extension.get("required", False)
            if uri is not None and (not isinstance(uri, str) or not uri.strip()):
                raise ValueError("AgentExtension uri must be a non-empty string")
            if type(required) is not bool:
                raise ValueError("AgentExtension required must be boolean")
            if required:
                required_extensions.append(str(uri or "<unspecified>"))
        return normalized, tuple(sorted(required_extensions))

    @staticmethod
    def _signatures(value: object) -> tuple[dict[str, object], ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError("signatures must be a list")
        normalized: list[dict[str, object]] = []
        for raw in value:
            if not isinstance(raw, Mapping):
                raise ValueError("AgentCardSignature must be an object")
            protected = raw.get("protected")
            signature = raw.get("signature")
            if not isinstance(protected, str) or not protected:
                raise ValueError("AgentCardSignature protected is required")
            if not isinstance(signature, str) or not signature:
                raise ValueError("AgentCardSignature signature is required")
            normalized.append(dict(raw))
        return tuple(normalized)

    @staticmethod
    def _required_string(value: Mapping[str, object], field: str) -> str:
        result = value.get(field)
        if not isinstance(result, str) or not result.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return result

    @staticmethod
    def _string_list(value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not value:
            raise ValueError(f"{field} must be a non-empty list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{field} must contain non-empty strings")
        return tuple(value)

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        """Deterministic CK evidence encoding; not an RFC 8785/JWS implementation."""
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    @staticmethod
    def _request_id(card: Mapping[str, object]) -> str:
        try:
            raw = A2AAgentCardAdmission._canonical_json(card)
        except (TypeError, ValueError):
            raw = b"invalid-agent-card"
        return f"a2a-card-{hashlib.sha256(raw).hexdigest()[:16]}"

    @staticmethod
    def _result(
        *,
        status: A2AAdmissionStatus,
        reason: str,
        access: ExternalAccessDecision,
        normalized: Mapping[str, object] | None = None,
        signature_state: str = "NOT_EVALUATED",
    ) -> A2AAdmissionResult:
        normalized = normalized or {}
        digest_payload = {
            "release": A2A_RELEASE_VERSION,
            "protocol": A2A_PROTOCOL_VERSION,
            "status": status.value,
            "reason": reason,
            "agent_name": normalized.get("name"),
            "agent_version": normalized.get("version"),
            "skill_ids": normalized.get("skill_ids", ()),
            "interface_bindings": normalized.get("interface_bindings", ()),
            "signature_state": signature_state,
            "access_reason": access.reason,
            "authority": "CK-NEXUS",
            "execution_allowed": False,
            "production_mutation_allowed": False,
            "verification_upgrade_allowed": False,
        }
        digest = hashlib.sha256(A2AAgentCardAdmission._canonical_json(digest_payload)).hexdigest()
        name = normalized.get("name")
        version = normalized.get("version")
        return A2AAdmissionResult(
            status=status,
            discovered=status is not A2AAdmissionStatus.REJECTED,
            admitted_candidate=status is A2AAdmissionStatus.DISCOVERED_CANDIDATE,
            execution_allowed=False,
            reason=reason,
            agent_name=name if isinstance(name, str) else None,
            agent_version=version if isinstance(version, str) else None,
            skill_ids=tuple(normalized.get("skill_ids", ())),
            interface_bindings=tuple(normalized.get("interface_bindings", ())),
            signature_state=signature_state,
            card_digest=digest,
            access_decision=access,
        )
