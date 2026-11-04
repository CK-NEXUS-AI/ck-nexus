from __future__ import annotations

import pytest

from creator_app.supply_chain_cosign import (
    CosignPolicyError,
    CosignVerificationIntent,
    validate_bundle_format,
    validate_cosign_version,
)


def _intent(**overrides):
    values = {
        "cosign_version": "3.1.3",
        "bundle_format": "standardized",
        "artifact_sha256": "a" * 64,
        "certificate_identity": "https://github.com/spinlnw10-art/ck-nexus/.github/workflows/release.yml",
        "oidc_issuer": "https://token.actions.githubusercontent.com",
    }
    values.update(overrides)
    return CosignVerificationIntent(**values)


def test_cosign_security_baseline_accepts_3_1_3_or_newer_v3() -> None:
    assert validate_cosign_version("3.1.3") == (3, 1, 3)
    assert validate_cosign_version("v3.2.0") == (3, 2, 0)


def test_cosign_security_baseline_rejects_vulnerable_and_unapproved_majors() -> None:
    with pytest.raises(CosignPolicyError, match="below_security_baseline"):
        validate_cosign_version("3.1.2")

    with pytest.raises(CosignPolicyError, match="major_not_approved"):
        validate_cosign_version("2.6.5")

    with pytest.raises(CosignPolicyError, match="major_not_approved"):
        validate_cosign_version("4.0.0")


def test_cosign_security_baseline_rejects_legacy_json_bundle() -> None:
    with pytest.raises(CosignPolicyError, match="legacy_or_unknown_bundle_format_denied"):
        validate_bundle_format("legacy-json")

    with pytest.raises(CosignPolicyError, match="legacy_or_unknown_bundle_format_denied"):
        _intent(bundle_format="legacy-json").validate()


def test_cosign_verification_intent_requires_artifact_identity_and_https_issuer() -> None:
    assert _intent().validate()

    with pytest.raises(CosignPolicyError, match="artifact_sha256_invalid"):
        _intent(artifact_sha256="not-a-digest").validate()

    with pytest.raises(CosignPolicyError, match="certificate_identity_invalid"):
        _intent(certificate_identity="").validate()

    with pytest.raises(CosignPolicyError, match="oidc_issuer_requires_https"):
        _intent(oidc_issuer="http://issuer.example").validate()


def test_cosign_evidence_is_bounded_and_does_not_copy_identity_or_issuer() -> None:
    intent = _intent()
    evidence = intent.evidence_projection()

    assert evidence["minimum_cosign_version"] == "3.1.3"
    assert evidence["standardized_bundle_only"] is True
    assert evidence["legacy_json_bundle_allowed"] is False
    assert evidence["artifact_sha256"] == "a" * 64
    assert len(evidence["certificate_identity_sha256"]) == 64
    assert len(evidence["oidc_issuer_sha256"]) == 64
    assert intent.certificate_identity not in str(evidence)
    assert intent.oidc_issuer not in str(evidence)
