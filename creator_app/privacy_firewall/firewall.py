"""Fail-closed privacy firewall with provenance-preserving redaction."""

from __future__ import annotations

import hashlib
import json
import re

from .contracts import (
    ContentEnvelope,
    DataClassification,
    DisclosureDecision,
    PrivacyPolicy,
    RedactionResult,
)

_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)")
_API_KEY_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})"
)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")

_CLASS_RANK = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.PERSONAL: 2,
    DataClassification.SENSITIVE: 3,
    DataClassification.SECRET: 4,
    DataClassification.REGULATED: 5,
}


class PrivacyBlocked(PermissionError):
    """Raised when data disclosure is denied by policy."""


def classify_and_redact(envelope: ContentEnvelope) -> RedactionResult:
    """Redact common personal/secret patterns without losing provenance taint."""
    content = envelope.content
    detected: set[DataClassification] = {envelope.classification}
    taints = set(envelope.taints)
    count = 0

    def replace(pattern: re.Pattern[str], marker: str, detected_class: DataClassification) -> None:
        nonlocal content, count
        content, hits = pattern.subn(marker, content)
        if hits:
            count += hits
            detected.add(detected_class)
            taints.add(f"detected:{detected_class.value}")

    replace(_PRIVATE_KEY_RE, "<redacted-private-key>", DataClassification.SECRET)
    replace(_API_KEY_RE, "<redacted-api-key>", DataClassification.SECRET)
    replace(_EMAIL_RE, "<redacted-email>", DataClassification.PERSONAL)
    replace(_PHONE_RE, "<redacted-phone>", DataClassification.PERSONAL)

    return RedactionResult(
        content=content,
        redaction_count=count,
        detected_classes=frozenset(detected),
        taints=frozenset(taints),
    )


def effective_classification(result: RedactionResult) -> DataClassification:
    """Return the highest-severity classification observed."""
    return max(result.detected_classes, key=lambda item: _CLASS_RANK[item])


def evaluate_disclosure(
    envelope: ContentEnvelope,
    *,
    destination: str,
    policy: PrivacyPolicy,
) -> DisclosureDecision:
    """Evaluate whether a destination may receive minimized content."""
    if not destination.strip():
        raise ValueError("destination must not be empty")
    redaction = classify_and_redact(envelope)
    classification = effective_classification(redaction)
    external = destination != "local"

    allowed = True
    reason = "local_processing_allowed"
    if external:
        if not policy.external_allowed:
            allowed = False
            reason = "external_processing_not_authorized"
        elif classification == DataClassification.REGULATED and not policy.regulated_external_consent:
            allowed = False
            reason = "regulated_external_consent_required"
        elif classification == DataClassification.SECRET:
            allowed = False
            reason = "secret_material_never_disclosed"
        elif classification == DataClassification.SENSITIVE and not policy.sensitive_external_consent:
            allowed = False
            reason = "sensitive_external_consent_required"
        elif classification == DataClassification.PERSONAL and not policy.personal_external_consent:
            allowed = False
            reason = "personal_external_consent_required"
        else:
            reason = "external_processing_authorized_with_minimization"

    evidence_payload = {
        "source": envelope.source,
        "purpose": envelope.purpose,
        "destination": destination,
        "classification": classification.value,
        "trust": envelope.trust.value,
        "taints": sorted(redaction.taints),
        "redaction_count": redaction.redaction_count,
        "allowed": allowed,
        "reason": reason,
        "authority": "CK-NEXUS",
        "raw_content_persisted": False,
    }
    encoded = json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode()
    evidence = {
        **evidence_payload,
        "decision_digest": hashlib.sha256(encoded).hexdigest(),
    }
    return DisclosureDecision(
        allowed=allowed,
        destination=destination,
        reason=reason,
        classification=classification,
        redacted_content=redaction.content,
        evidence=evidence,
    )


def require_disclosure(
    envelope: ContentEnvelope,
    *,
    destination: str,
    policy: PrivacyPolicy,
) -> DisclosureDecision:
    decision = evaluate_disclosure(envelope, destination=destination, policy=policy)
    if not decision.allowed:
        raise PrivacyBlocked(decision.reason)
    return decision
