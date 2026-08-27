from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SubjectValidationError(ValueError):
    """Raised when a verification subject cannot be bound deterministically."""


class SubjectComponent(StrEnum):
    SOURCE = "SOURCE"
    TREE = "TREE"
    ARCHIVE = "ARCHIVE"
    ENVIRONMENT = "ENVIRONMENT"
    PLAN = "PLAN"
    DEPENDENCY = "DEPENDENCY"
    POLICY = "POLICY"
    TOOLCHAIN = "TOOLCHAIN"


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 of canonical JSON without leaking Python object ordering."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_public_environment(environment: dict[str, Any]) -> str:
    """Hash a sanitized environment descriptor, never raw process environment.

    Callers must pass only non-secret descriptors such as runtime version,
    OS/kernel, sandbox/runtime policy identifiers, architecture and image digest.
    Secret values, bearer tokens, API keys and passwords are not valid subject
    material and must remain behind the CK-NEXUS credential boundary.
    """

    forbidden_fragments = ("secret", "token", "password", "api_key", "private_key")
    for key in environment:
        normalized = str(key).casefold()
        if any(fragment in normalized for fragment in forbidden_fragments):
            raise SubjectValidationError("secret-like environment key is not admissible")
    return canonical_sha256(environment)


@dataclass(frozen=True, slots=True)
class VerificationSubject:
    repository: str
    repository_sha: str
    tree_sha: str
    environment_digest: str
    plan_digest: str
    dependency_digest: str
    policy_digest: str
    toolchain_digest: str
    archive_digest: str | None = None
    schema_version: str = "1.0"

    def validate(self) -> None:
        if not self.repository.strip():
            raise SubjectValidationError("repository is required")
        if not _SHA40_RE.fullmatch(self.repository_sha):
            raise SubjectValidationError("repository_sha must be lowercase 40-hex Git SHA")
        if not _SHA40_RE.fullmatch(self.tree_sha):
            raise SubjectValidationError("tree_sha must be lowercase 40-hex Git tree SHA")
        for name in (
            "environment_digest",
            "plan_digest",
            "dependency_digest",
            "policy_digest",
            "toolchain_digest",
        ):
            value = getattr(self, name)
            if not _SHA256_RE.fullmatch(value):
                raise SubjectValidationError(f"{name} must be lowercase SHA-256")
        if self.archive_digest is not None and not _SHA256_RE.fullmatch(self.archive_digest):
            raise SubjectValidationError("archive_digest must be lowercase SHA-256")
        if self.schema_version != "1.0":
            raise SubjectValidationError("unsupported verification-subject schema version")

    def canonical_payload(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @property
    def digest(self) -> str:
        return canonical_sha256(self.canonical_payload())

    @property
    def subject_id(self) -> str:
        """Stable human-facing identifier; the full digest remains authoritative."""

        return f"VFY-{self.digest[:16].upper()}"

    def changed_components(self, previous: VerificationSubject) -> frozenset[SubjectComponent]:
        """Return exact dimensions that changed between two locked subjects."""

        self.validate()
        previous.validate()
        changed: set[SubjectComponent] = set()
        if self.repository != previous.repository or self.repository_sha != previous.repository_sha:
            changed.add(SubjectComponent.SOURCE)
        if self.tree_sha != previous.tree_sha:
            changed.add(SubjectComponent.TREE)
        if self.archive_digest != previous.archive_digest:
            changed.add(SubjectComponent.ARCHIVE)
        if self.environment_digest != previous.environment_digest:
            changed.add(SubjectComponent.ENVIRONMENT)
        if self.plan_digest != previous.plan_digest:
            changed.add(SubjectComponent.PLAN)
        if self.dependency_digest != previous.dependency_digest:
            changed.add(SubjectComponent.DEPENDENCY)
        if self.policy_digest != previous.policy_digest:
            changed.add(SubjectComponent.POLICY)
        if self.toolchain_digest != previous.toolchain_digest:
            changed.add(SubjectComponent.TOOLCHAIN)
        return frozenset(changed)
