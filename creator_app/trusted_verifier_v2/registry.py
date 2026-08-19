"""Lifecycle and trust-tuple registry for CK-NEXUS verifier images."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]*@sha256:[0-9a-f]{64}$")


class VerifierState(StrEnum):
    CANDIDATE = "candidate"
    BUILT = "built"
    SCANNED = "scanned"
    ATTESTED = "attested"
    TRUSTED = "trusted"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class VerifierProfile(StrEnum):
    PYTHON_QUALITY = "python_quality"
    PYTHON_SECURITY = "python_security"
    API_CONTRACT = "api_contract"
    FRONTEND_QUALITY = "frontend_quality"
    CONNECTOR_SECURITY = "connector_security"
    DATABASE_MIGRATION = "database_migration"
    DEPENDENCY_CHANGE = "dependency_change"
    CONTAINER_IMAGE = "container_image"
    INFRASTRUCTURE = "infrastructure"


@dataclass(frozen=True, slots=True)
class TrustedVerifierEntry:
    image_ref: str
    source_commit: str
    entrypoint_digest: str
    policy_digest: str
    sbom_digest: str
    build_provenance_digest: str
    profile: VerifierProfile
    state: VerifierState = VerifierState.CANDIDATE

    def __post_init__(self) -> None:
        if not _IMAGE_RE.fullmatch(self.image_ref):
            raise ValueError("image_ref must be registry digest pinned")
        if not _SHA1_RE.fullmatch(self.source_commit):
            raise ValueError("source_commit must be exact lowercase 40-character Git SHA")
        for value in (
            self.entrypoint_digest,
            self.policy_digest,
            self.sbom_digest,
            self.build_provenance_digest,
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError("verifier trust digests must be lowercase SHA-256")


class VerifierTrustDenied(PermissionError):
    """Raised when a verifier image/profile is not active and trusted."""


class TrustedVerifierRegistry:
    """Explicit verifier allowlist with rotation and immediate revocation."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, VerifierProfile], TrustedVerifierEntry] = {}

    def register(self, entry: TrustedVerifierEntry) -> None:
        key = (entry.image_ref, entry.profile)
        if key in self._entries:
            raise ValueError("verifier entry already registered")
        self._entries[key] = entry

    def transition(
        self,
        image_ref: str,
        profile: VerifierProfile,
        state: VerifierState,
    ) -> TrustedVerifierEntry:
        key = (image_ref, profile)
        current = self._entries.get(key)
        if current is None:
            raise KeyError("verifier entry not registered")
        if current.state == VerifierState.REVOKED and state != VerifierState.REVOKED:
            raise VerifierTrustDenied("revoked verifier cannot be reactivated")
        if state == VerifierState.ACTIVE:
            for other_key, other in tuple(self._entries.items()):
                if other.profile == profile and other.state == VerifierState.ACTIVE:
                    self._entries[other_key] = replace(other, state=VerifierState.DEPRECATED)
        updated = replace(current, state=state)
        self._entries[key] = updated
        return updated

    def revoke(self, image_ref: str, profile: VerifierProfile) -> TrustedVerifierEntry:
        return self.transition(image_ref, profile, VerifierState.REVOKED)

    def require_active(
        self,
        *,
        image_ref: str,
        profile: VerifierProfile,
        policy_digest: str,
    ) -> TrustedVerifierEntry:
        entry = self._entries.get((image_ref, profile))
        if entry is None:
            raise VerifierTrustDenied("verifier image/profile is not registered")
        if entry.state != VerifierState.ACTIVE:
            raise VerifierTrustDenied("verifier image/profile is not active")
        if entry.policy_digest != policy_digest:
            raise VerifierTrustDenied("verifier policy digest mismatch")
        return entry

    def active(self, profile: VerifierProfile) -> TrustedVerifierEntry | None:
        for entry in self._entries.values():
            if entry.profile == profile and entry.state == VerifierState.ACTIVE:
                return entry
        return None
