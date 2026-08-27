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


class A2AAdmissionStatus(StrEnum):
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    DISCOVERED_CANDIDATE = "DISCOVERED_CANDIDATE"


class AgentCardSignatureVerifier(Protocol):
    """Trusted JWS verifier boundary supplied by the CK Verification Plane."""

    def verify(
        self,
        *,
        unsigned_card: bytes,
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
        expected_host = expected_host.strip().lower()
        if not expected_host:
            raise ValueError("expected_host must not be empty")

        access_request = ExternalAccessRequest(
            request_id=self._request_id(card),
            source=f"https://{expected_host}{A2A_AGENT_CARD_WELL_KNOWN_PATH}",
            access_class=ExternalAccessClass.PUBLIC_WEB,
            action=ExternalAction.READ,
            purpose="a2a-agent-card-discovery",
            user_authorized=user_authorized,
        )
        access_decision = self._access_governor.evaluate(access_request)
        if access_decision.outcome is not AccessOutcome.ALLOW:
            return self._result(
                status=A2AAdmissionStatus.REJECTED,
                reason=f"external_access_denied:{access_decision.reason}",
                access_decision=access_decision,
            )

        try:
            normalized = self._validate_card(card, expected_host=expected_host)
        except (TypeError, ValueError) as exc:
            return self._result(
                status=A2AAdmissionStatus.REJECTED,
                reason=f"invalid_agent_card:{exc}",
                access_decision=access_decision,
            )

        signatures = normalized.pop("signatures", ())
        signature_state = "ABSENT"
        if signatures:
            if self._signature_verifier is None:
                return self._result(
                    status=A2AAdmissionStatus.QUARANTINED,
                    reason="agent_card_signature_present_but_no_trusted_verifier",
                    access_decision=access_decision,
                    normalized=normalized,
                    signature_state="UNVERIFIED",
                )
            unsigned = self._canonical_json(normalized)
            try:
                signature_ok = self._signature_verifier.verify(
                    unsigned_card=unsigned,
                    signatures=signatures,
                )
            except (KeyError, TypeError, ValueError):
                signature_ok = False
            if not signature_ok:
                return self._result(
                    status=A2AAdmissionStatus.REJECTED,
                    reason="agent_card_signature_verification_failed",
                    access_decision=access_decision,
                    normalized=normalized,
                    signature_state="FAILED",
                )
            signature_state = "VERIFIED_BY_TRUSTED_BOUNDARY"

        if normalized["required_extensions"]:
            return self._result(
                status=A2AAdmissionStatus.QUARANTINED,
                reason="required_a2a_extension_requires_explicit_ck_admission",
                access_decision=access_decision,
                normalized=normalized,
                signature_state=signature_state,
            )

        return self._result(
            status=A2AAdmissionStatus.DISCOVERED_CANDIDATE,
            reason="agent_card_valid_for_non_executable_discovery",
            access_decision=access_decision,
            normalized=normalized,
            signature_state=signature_state,
        )

    @staticmethod
    def _validate_card(
        card: Mapping[str, object],
        *,
        expected_host: str,
    ) -> dict[str, object]:
        if not isinstance(card, Mapping):
            raise TypeError("Agent Card must be an object")
        allowed = {
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
        unknown = set(card) - allowed
        if unknown:
            raise ValueError(f"unsupported Agent Card fields: {sorted(unknown)}")

        name = A2AAgentCardAdmission._required_string(card, "name")
        description = A2AAgentCardAdmission._required_string(card, "description")
        version = A2AAgentCardAdmission._required_string(card, "version")
        input_modes = A2AAgentCardAdmission._string_list(card.get("defaultInputModes"), "defaultInputModes")
        output_modes = A2AAgentCardAdmission._string_list(
            card.get("defaultOutputModes"),
            "defaultOutputModes",
        )
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
            "name": name,
            "description": description,
            "supportedInterfaces": interfaces,
            "version": version,
            "capabilities": capabilities,
            "defaultInputModes": input_modes,
            "defaultOutputModes": output_modes,
            "skills": skills,
            "skill_ids": skill_ids,
            "interface_bindings": bindings,
            "required_extensions": required_extensions,
            "signatures": signatures,
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
        json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        return normalized

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
            unknown = set(raw) - {"url", "protocolBinding", "tenant", "protocolVersion"}
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
            except (ValueError, TypeError):
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
        required_extensions: list[str] = []
        extensions = value.get("extensions", [])
        if not isinstance(extensions, list):
            raise ValueError("capabilities.extensions must be a list")
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
        for signature in value:
            if not isinstance(signature, Mapping):
                raise ValueError("AgentCardSignature must be an object")
            protected = signature.get("protected")
            encoded = signature.get("signature")
            if not isinstance(protected, str) or not protected:
                raise ValueError("AgentCardSignature protected is required")
            if not isinstance(encoded, str) or not encoded:
                raise ValueError("AgentCardSignature signature is required")
            normalized.append(dict(signature))
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
        access_decision: ExternalAccessDecision,
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
            "access_reason": access_decision.reason,
            "authority": "CK-NEXUS",
            "execution_allowed": False,
            "production_mutation_allowed": False,
            "verification_upgrade_allowed": False,
        }
        digest = hashlib.sha256(A2AAgentCardAdmission._canonical_json(digest_payload)).hexdigest()
        return A2AAdmissionResult(
            status=status,
            discovered=status is not A2AAdmissionStatus.REJECTED,
            admitted_candidate=status is A2AAdmissionStatus.DISCOVERED_CANDIDATE,
            execution_allowed=False,
            reason=reason,
            agent_name=normalized.get("name") if isinstance(normalized.get("name"), str) else None,
            agent_version=(
                normalized.get("version") if isinstance(normalized.get("version"), str) else None
            ),
            skill_ids=tuple(normalized.get("skill_ids", ())),
            interface_bindings=tuple(normalized.get("interface_bindings", ())),
            signature_state=signature_state,
            card_digest=digest,
            access_decision=access_decision,
        )
