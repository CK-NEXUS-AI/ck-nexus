"""Redacted evidence envelopes for development-assistant execution results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    """Append-only compatible observation metadata without raw provider output."""

    execution_id: str
    assistant_id: str
    result_state: str
    patch_digest: str | None = None
    stdout_digest: str | None = None
    stderr_digest: str | None = None
    exit_code: int | None = None
    verifier: str = "cknexus_independent_verifier"
    release_evidence: bool = False
    production_status: str = "NO-GO"

    def __post_init__(self) -> None:
        if not self.execution_id.startswith("devexec-"):
            raise ValueError("execution_id must use the devexec- identity namespace")
        if not self.assistant_id.strip():
            raise ValueError("assistant_id must not be empty")
        if self.release_evidence:
            raise ValueError("development execution evidence cannot be release evidence")
        for digest in (self.patch_digest, self.stdout_digest, self.stderr_digest):
            if digest is not None and not _is_sha256(digest):
                raise ValueError("output digests must be lowercase SHA-256 hex")

    def envelope(self) -> dict[str, Any]:
        """Return a canonical redacted envelope plus its evidence digest."""
        payload = asdict(self)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return {
            "evidence": payload,
            "evidence_digest": hashlib.sha256(encoded).hexdigest(),
            "raw_output_included": False,
            "authority": "CK-NEXUS",
        }


def digest_bytes(data: bytes) -> str:
    """Return a SHA-256 digest for sandbox output without storing its raw value."""
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)
