"""Fail-closed Cosign verification baseline for CK-NEXUS local evaluation.

This policy module does not invoke Cosign, fetch transparency data, or sign artifacts. It validates
operator-supplied verification intent before any future executor may call Cosign.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

COSIGN_BASELINE_VERSION = "3.1.3"
COSIGN_ALLOWED_MAJOR = 3
STANDARDIZED_BUNDLE_FORMAT = "standardized"

_HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")
_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class CosignPolicyError(ValueError):
    """Raised when supply-chain verification intent violates the CK-NEXUS baseline."""


def parse_cosign_version(value: str) -> tuple[int, int, int]:
    """Parse a stable semantic version and reject prerelease/build suffixes fail-closed."""
    match = _VERSION.fullmatch(value.strip())
    if match is None:
        raise CosignPolicyError("cosign_version_invalid")
    return tuple(int(part) for part in match.groups())


def validate_cosign_version(value: str) -> tuple[int, int, int]:
    """Require the CK-NEXUS v3 baseline at or above 3.1.3."""
    version = parse_cosign_version(value)
    if version[0] != COSIGN_ALLOWED_MAJOR:
        raise CosignPolicyError("cosign_major_not_approved")
    if version < (3, 1, 3):
        raise CosignPolicyError("cosign_version_below_security_baseline")
    return version


def validate_bundle_format(value: str) -> str:
    """Permit only the standardized bundle path; legacy JSON is denied."""
    normalized = value.strip().lower()
    if normalized != STANDARDIZED_BUNDLE_FORMAT:
        raise CosignPolicyError("legacy_or_unknown_bundle_format_denied")
    return normalized


def _validate_https_issuer(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise CosignPolicyError("oidc_issuer_requires_https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CosignPolicyError("oidc_issuer_contains_forbidden_components")
    return value.strip().rstrip("/")


def _identity_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CosignVerificationIntent:
    """Non-secret inputs required before a future Cosign verifier may execute."""

    cosign_version: str
    bundle_format: str
    artifact_sha256: str
    certificate_identity: str
    oidc_issuer: str

    def validate(self) -> CosignVerificationIntent:
        validate_cosign_version(self.cosign_version)
        validate_bundle_format(self.bundle_format)
        if not _HEX_64.fullmatch(self.artifact_sha256):
            raise CosignPolicyError("artifact_sha256_invalid")
        identity = self.certificate_identity.strip()
        if not identity or len(identity) > 512 or "\n" in identity or "\r" in identity:
            raise CosignPolicyError("certificate_identity_invalid")
        _validate_https_issuer(self.oidc_issuer)
        return self

    def evidence_projection(self) -> dict[str, str | bool]:
        """Return bounded evidence without copying certificate identity or issuer verbatim."""
        self.validate()
        return {
            "policy": "CKNEXUS_COSIGN_BASELINE_V1",
            "minimum_cosign_version": COSIGN_BASELINE_VERSION,
            "cosign_version": self.cosign_version.lstrip("v"),
            "standardized_bundle_only": True,
            "legacy_json_bundle_allowed": False,
            "artifact_sha256": self.artifact_sha256.lower(),
            "certificate_identity_sha256": _identity_digest(self.certificate_identity.strip()),
            "oidc_issuer_sha256": _identity_digest(_validate_https_issuer(self.oidc_issuer)),
        }
