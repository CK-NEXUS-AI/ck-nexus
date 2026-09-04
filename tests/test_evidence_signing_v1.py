from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from creator_app.evidence_signing import (
    EvidenceCustodyLedger,
    EvidenceSubject,
    SignerType,
    SignatureStatus,
    build_manifest,
    evaluate_signature_policy,
    unsigned_signature_envelope,
    verify_chain_export,
    verify_cosign_bundle,
    verify_manifest,
)


def _subject() -> EvidenceSubject:
    return EvidenceSubject(
        repository="spinlnw10-art/ck-nexus",
        commit="a" * 40,
        tree="b" * 40,
        environment="test",
        scanner="unit-test",
        scanner_version="1.0",
        run_id="42",
    )


def test_manifest_binds_exact_artifact_hashes(tmp_path: Path):
    (tmp_path / "findings.json").write_text('{"findings": []}\n', encoding="utf-8")
    (tmp_path / "coverage.json").write_text('{"coverage": 1}\n', encoding="utf-8")
    manifest = build_manifest(
        root=tmp_path,
        subject=_subject(),
        artifacts=["findings.json", "coverage.json"],
        observed_at="2026-09-04T00:00:00+00:00",
    )
    state = verify_manifest(tmp_path, manifest)
    assert state["valid"] is True
    assert manifest["trust"]["production_effect"] == "NONE"
    assert manifest["trust"]["independent_human_review"] == "PENDING"


def test_manifest_detects_artifact_tampering(tmp_path: Path):
    artifact = tmp_path / "findings.json"
    artifact.write_text('{"findings": []}\n', encoding="utf-8")
    manifest = build_manifest(root=tmp_path, subject=_subject(), artifacts=["findings.json"])
    artifact.write_text('{"findings": ["tampered"]}\n', encoding="utf-8")
    state = verify_manifest(tmp_path, manifest)
    assert state["valid"] is False
    assert any("sha256 mismatch" in failure for failure in state["failures"])


def test_manifest_rejects_path_escape_and_symlink(tmp_path: Path):
    outside = tmp_path.parent / "outside-evidence.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes evidence root"):
        build_manifest(root=tmp_path, subject=_subject(), artifacts=["../outside-evidence.txt"])

    target = tmp_path / "target.txt"
    target.write_text("safe", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        build_manifest(root=tmp_path, subject=_subject(), artifacts=["link.txt"])


def test_chain_of_custody_reuses_append_only_ledger_and_detects_tamper(tmp_path: Path):
    ledger = EvidenceCustodyLedger(tmp_path / "custody.jsonl")
    first = ledger.append(
        action="MANIFEST_CREATED",
        actor_type=SignerType.SYSTEM,
        actor_id="system",
        manifest_sha256="1" * 64,
    )
    second = ledger.append(
        action="SYSTEM_SIGNATURE_REQUESTED",
        actor_type=SignerType.SYSTEM,
        actor_id="system",
        manifest_sha256="1" * 64,
    )
    assert second["previous_hash"] == first["hash"]

    exported = ledger.export(tmp_path / "chain-of-custody.json")
    assert verify_chain_export(exported)["valid"] is True

    exported["entries"][0]["payload"]["action"] = "TAMPERED"
    assert verify_chain_export(exported)["valid"] is False


def test_system_signature_never_counts_as_independent_human_or_owner():
    envelope = unsigned_signature_envelope("a" * 64)
    envelope["signers"][0]["status"] = SignatureStatus.CRYPTOGRAPHICALLY_VERIFIED.value
    state = evaluate_signature_policy(envelope)
    assert state["system_integrity"] is True
    assert state["independent_human_review"] is False
    assert state["owner_signoff"] is False
    assert state["production_authorized"] is False
    assert state["release_gate_effect"] == "NONE"


def test_cosign_verification_rejects_legacy_bundle(tmp_path: Path):
    blob = tmp_path / "manifest.json"
    blob.write_text("{}\n", encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    bundle.write_text('{"base64Signature": "legacy"}\n', encoding="utf-8")

    version = Mock(returncode=0, stdout="GitVersion: v3.1.3", stderr="")
    with patch("creator_app.evidence_signing.subprocess.run", return_value=version):
        with pytest.raises(RuntimeError, match="legacy/non-standard"):
            verify_cosign_bundle(
                blob=blob,
                bundle=bundle,
                certificate_identity="ci@example.invalid",
                certificate_oidc_issuer="https://token.actions.githubusercontent.com",
            )


def test_cosign_verification_requires_patched_version(tmp_path: Path):
    blob = tmp_path / "manifest.json"
    blob.write_text("{}\n", encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps({"mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json"}),
        encoding="utf-8",
    )

    old = Mock(returncode=0, stdout="GitVersion: v3.1.2", stderr="")
    with patch("creator_app.evidence_signing.subprocess.run", return_value=old):
        with pytest.raises(RuntimeError, match="3.1.3 or newer"):
            verify_cosign_bundle(
                blob=blob,
                bundle=bundle,
                certificate_identity="ci@example.invalid",
                certificate_oidc_issuer="https://token.actions.githubusercontent.com",
            )


def test_cosign_standard_bundle_can_be_verified_with_identity_policy(tmp_path: Path):
    blob = tmp_path / "manifest.json"
    blob.write_text("{}\n", encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    bundle.write_text(
        json.dumps({"mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json"}),
        encoding="utf-8",
    )

    version = Mock(returncode=0, stdout="GitVersion: v3.1.3", stderr="")
    verify = Mock(returncode=0, stdout="Verified OK", stderr="")
    with patch(
        "creator_app.evidence_signing.subprocess.run",
        side_effect=[version, verify],
    ) as run:
        state = verify_cosign_bundle(
            blob=blob,
            bundle=bundle,
            certificate_identity="ci@example.invalid",
            certificate_oidc_issuer="https://token.actions.githubusercontent.com",
        )

    assert state["valid"] is True
    assert state["cosign_version"] == "3.1.3"
    verify_args = run.call_args_list[1].args[0]
    assert "--certificate-identity" in verify_args
    assert "--certificate-oidc-issuer" in verify_args
