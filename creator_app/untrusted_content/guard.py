"""Prompt-injection and authority-confusion guard for untrusted external content."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from creator_app.privacy_firewall import ContentEnvelope, TrustLevel


@dataclass(frozen=True, slots=True)
class GuardResult:
    trusted_for_instructions: bool
    risk_flags: tuple[str, ...]
    content_digest: str
    allowed_effects: tuple[str, ...] = ()


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(r"\b(?:ignore|forget|override)\b.{0,40}\b(?:instruction|system|policy)\b", re.I),
    ),
    (
        "credential_request",
        re.compile(r"\b(?:api[-_ ]?key|token|password|private key|credential)\b", re.I),
    ),
    (
        "execution_request",
        re.compile(r"\b(?:run|execute|shell|bash|powershell|terminal)\b", re.I),
    ),
    (
        "authority_claim",
        re.compile(r"\b(?:system message|administrator|root authority|developer instruction)\b", re.I),
    ),
)


def inspect_untrusted_content(envelope: ContentEnvelope) -> GuardResult:
    """External content may provide data but can never elevate itself into authority."""
    digest = hashlib.sha256(envelope.content.encode()).hexdigest()
    if envelope.trust == TrustLevel.AUTHORITATIVE:
        return GuardResult(True, (), digest, ("data", "instruction"))
    flags = tuple(name for name, pattern in _PATTERNS if pattern.search(envelope.content))
    return GuardResult(
        trusted_for_instructions=False,
        risk_flags=flags,
        content_digest=digest,
        allowed_effects=("data",),
    )
