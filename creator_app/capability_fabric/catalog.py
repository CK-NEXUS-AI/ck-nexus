"""Typed catalog that keeps providers, tools, plugins, skills and workflows distinct.

The catalog is descriptive only: listing an artifact never grants credentials,
execution rights, write activation, or CK-NEXUS authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ArtifactClass(StrEnum):
    CORE = "core"
    AI_PROVIDER = "ai_provider"
    AI_GATEWAY = "ai_gateway"
    AGENT_FRAMEWORK = "agent_framework"
    TOOL = "tool"
    PLUGIN = "plugin"
    CONNECTOR = "connector"
    SKILL = "skill"
    WORKFLOW_ENGINE = "workflow_engine"
    KNOWLEDGE_SOURCE = "knowledge_source"
    DOCUMENT_PARSER = "document_parser"
    VECTOR_STORE = "vector_store"
    OBSERVABILITY = "observability"
    SANDBOX = "sandbox"
    UNKNOWN = "unknown"


class ArtifactStatus(StrEnum):
    PRESENT = "present"
    PARTIAL = "partial"
    DISCOVERY_ONLY = "discovery_only"
    NOT_INSTALLED = "not_installed"
    BLOCKED = "blocked"


VERIFICATION_STATE_KEYS = frozenset(
    {
        "discovered",
        "available_in_chat_session",
        "online_verified",
        "not_connected",
        "not_integrated",
        "runtime_verified",
    }
)


@dataclass(frozen=True, slots=True)
class VerificationState:
    discovered: bool
    available_in_chat_session: bool
    online_verified: bool
    not_connected: bool
    not_integrated: bool
    runtime_verified: bool

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> VerificationState:
        if set(raw) != VERIFICATION_STATE_KEYS:
            raise ValueError("verification_state must contain exactly the six independent status fields")
        if any(type(raw[key]) is not bool for key in VERIFICATION_STATE_KEYS):
            raise ValueError("verification_state fields must be booleans")
        if not raw["discovered"] and any(raw[key] for key in VERIFICATION_STATE_KEYS - {"discovered"}):
            raise ValueError("verification_state flags require discovered=true")
        if raw["not_connected"] and not raw["not_integrated"]:
            raise ValueError("not_connected requires not_integrated")
        if raw["runtime_verified"] and (raw["not_connected"] or raw["not_integrated"]):
            raise ValueError("runtime_verified requires connected and integrated")
        return cls(**raw)


@dataclass(frozen=True, slots=True)
class CapabilityArtifact:
    artifact_id: str
    name: str
    artifact_class: ArtifactClass
    status: ArtifactStatus
    integration_point: str
    authority_scope: str
    license: str = "unknown"
    source_url: str | None = None
    capabilities: tuple[str, ...] = ()
    notes: str = ""
    verification_state: VerificationState | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> CapabilityArtifact:
        required = ("id", "name", "class", "status", "integration_point", "authority_scope")
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required):
            raise ValueError("capability artifact has an empty required field")
        artifact_class = ArtifactClass(raw["class"])
        status = ArtifactStatus(raw["status"])
        source_url = raw.get("source_url")
        if source_url is not None and (
            not isinstance(source_url, str) or not source_url.startswith(("https://", "http://"))
        ):
            raise ValueError("source_url must be http(s)")
        capabilities = raw.get("capabilities", [])
        if not isinstance(capabilities, list) or any(
            not isinstance(value, str) or not value.strip() for value in capabilities
        ):
            raise ValueError("capabilities must be a list of non-empty strings")
        raw_verification = raw.get("verification_state")
        verification_state = (
            VerificationState.from_mapping(raw_verification)
            if raw_verification is not None
            else None
        )
        # Only CK-NEXUS Core may be assigned the internal L3 authority scope.
        authority_scope = raw["authority_scope"]
        if artifact_class is ArtifactClass.CORE:
            if authority_scope != "L3":
                raise ValueError("CK-NEXUS Core must declare L3 authority")
        elif authority_scope != "NONE":
            raise ValueError("external artifacts must have authority_scope=NONE")
        return cls(
            artifact_id=raw["id"],
            name=raw["name"],
            artifact_class=artifact_class,
            status=status,
            integration_point=raw["integration_point"],
            authority_scope=authority_scope,
            license=str(raw.get("license", "unknown")),
            source_url=source_url,
            capabilities=tuple(capabilities),
            notes=str(raw.get("notes", "")),
            verification_state=verification_state,
        )


class CapabilityCatalog:
    """Load and query a versioned inventory; it is never an execution registry."""

    def __init__(self, artifacts: tuple[CapabilityArtifact, ...], version: str) -> None:
        ids = [item.artifact_id for item in artifacts]
        if len(ids) != len(set(ids)):
            raise ValueError("capability artifact ids must be unique")
        self.version = version
        self._artifacts = tuple(sorted(artifacts, key=lambda item: item.artifact_id))
        self._by_id = {item.artifact_id: item for item in self._artifacts}

    @classmethod
    def load(cls, path: str | Path) -> CapabilityCatalog:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("capability catalog could not be read") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
            raise ValueError("unsupported capability catalog schema")
        raw_artifacts = payload.get("artifacts")
        if not isinstance(raw_artifacts, list):
            raise ValueError("capability catalog artifacts must be a list")
        artifacts = tuple(
            CapabilityArtifact.from_mapping(item)
            for item in raw_artifacts
            if isinstance(item, dict)
        )
        if len(artifacts) != len(raw_artifacts):
            raise ValueError("capability catalog contains an invalid artifact")
        return cls(artifacts, payload["schema_version"])

    def list(self) -> tuple[CapabilityArtifact, ...]:
        return self._artifacts

    def get(self, artifact_id: str) -> CapabilityArtifact:
        try:
            return self._by_id[artifact_id]
        except KeyError:
            raise KeyError("unknown capability artifact") from None

    def by_class(self, artifact_class: ArtifactClass) -> tuple[CapabilityArtifact, ...]:
        return tuple(item for item in self._artifacts if item.artifact_class is artifact_class)

    def by_status(self, status: ArtifactStatus) -> tuple[CapabilityArtifact, ...]:
        return tuple(item for item in self._artifacts if item.status is status)
