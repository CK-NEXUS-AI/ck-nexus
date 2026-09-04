from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_app.evidence_signing.bundle import (
    EvidenceBundleError,
    build_evidence_bundle,
    record_system_signature,
    verify_evidence_bundle,
)
from creator_app.evidence_signing.cosign import sign_and_verify_keyless
from creator_app.evidence_signing.openssl_ed25519 import sign_and_verify_ed25519

COMMIT = "1" * 40
TREE = "2" * 40


def _evidence(root: Path) -> Path:
    root.mkdir()
    (root / "scan-manifest.json").write_text('{"scanner":"demo"}\n', encoding="utf-8")
    (root / "findings.json").write_text('{"findings":[]}\n', encoding="utf-8")
    (root / "coverage.json").write_text('{"coverage":"measured"}\n', encoding="utf-8")
    (root / "report.md").write_text("# Report\n\nDevelopment evidence.\n", encoding="utf-8")
    return root


def _build(tmp_path: Path) -> tuple[Path, Path]:
    evidence = _evidence(tmp_path / "evidence")
    output = tmp_path / "bundle"
    build_evidence_bundle(
        evidence_dir=evidence,
        output_dir=output,
        repository="spinlnw10-art/ck-nexus",
        subject_commit=COMMIT,
        subject_tree=TREE,
        scanner="demo-scanner",
        scanner_version="1.0",
        run_id="run-1",
        observed_at="2026-09-04T00:00:00+00:00",
    )
    return evidence, output


def test_build_binds_required_artifacts_and_keeps_fail_closed_state(tmp_path: Path) -> None:
    evidence, output = _build(tmp_path)
    manifest = json.loads((output / "evidence-signing-manifest.json").read_text())
    state = json.loads((output / "verification-state.json").read_text())

    assert [item["path"] for item in manifest["artifacts"]] == [
        "coverage.json",
        "findings.json",
        "report.md",
        "scan-manifest.json",
    ]
    assert state["system_signature"]["status"] == "NOT_SIGNED"
    assert state["independent_human_review"]["status"] == "PENDING"
    assert state["owner_signoff"]["status"] == "PENDING"
    assert state["q10"] == "NOT_VERIFIED"
    assert state["production"] == "NO-GO"
    assert verify_evidence_bundle(evidence_dir=evidence, output_dir=output)["result"] == "PASS"


def test_missing_required_evidence_fails_closed(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path / "evidence")
    (evidence / "coverage.json").unlink()

    with pytest.raises(EvidenceBundleError, match="coverage.json"):
        build_evidence_bundle(
            evidence_dir=evidence,
            output_dir=tmp_path / "out",
            repository="spinlnw10-art/ck-nexus",
            subject_commit=COMMIT,
            subject_tree=TREE,
            scanner="demo",
            scanner_version="1",
        )


def test_artifact_tamper_is_detected(tmp_path: Path) -> None:
    evidence, output = _build(tmp_path)
    (evidence / "report.md").write_text("tampered\n", encoding="utf-8")

    result = verify_evidence_bundle(evidence_dir=evidence, output_dir=output)

    assert result["result"] == "FAIL"
    assert "hash_mismatch:report.md" in result["failures"]


def test_chain_tamper_is_detected(tmp_path: Path) -> None:
    evidence, output = _build(tmp_path)
    chain_path = output / "chain-of-custody.json"
    chain = json.loads(chain_path.read_text())
    chain["entries"][0]["action"] = "FORGED"
    chain_path.write_text(json.dumps(chain), encoding="utf-8")

    result = verify_evidence_bundle(evidence_dir=evidence, output_dir=output)

    assert result["result"] == "FAIL"
    assert "chain_invalid" in result["failures"]


def test_sigstore_keyless_requires_explicit_public_log_authorization(tmp_path: Path) -> None:
    _, output = _build(tmp_path)

    with pytest.raises(EvidenceBundleError, match="explicit public transparency-log"):
        sign_and_verify_keyless(
            manifest_path=output / "evidence-signing-manifest.json",
            bundle_path=output / "sigstore.json",
            signer_identity="https://github.com/example/workflow",
            oidc_issuer="https://token.actions.githubusercontent.com",
            cosign_path="/fake/cosign",
        )


def test_verified_system_signature_never_promotes_human_or_production_state(
    tmp_path: Path,
) -> None:
    evidence, output = _build(tmp_path)
    calls: list[list[str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[1] == "sign-blob":
            bundle_index = command.index("--bundle") + 1
            Path(command[bundle_index]).write_text('{"mediaType":"sigstore"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    signed = sign_and_verify_keyless(
        manifest_path=output / "evidence-signing-manifest.json",
        bundle_path=output / "evidence-signing.sigstore.json",
        signer_identity="https://github.com/spinlnw10-art/ck-nexus/.github/workflows/demo.yml",
        oidc_issuer="https://token.actions.githubusercontent.com",
        allow_public_transparency_log=True,
        cosign_path="/fake/cosign",
        runner=runner,
    )
    state = record_system_signature(
        output_dir=output,
        provider="sigstore-cosign-keyless",
        bundle_filename=signed.bundle_path.name,
        signer_identity=signed.signer_identity,
        verified_at="2026-09-04T00:01:00+00:00",
    )

    assert [command[1] for command in calls] == ["sign-blob", "verify-blob"]
    assert state["system_signature"]["status"] == "CRYPTOGRAPHICALLY_VERIFIED"
    assert state["independent_human_review"]["status"] == "PENDING"
    assert state["owner_signoff"]["status"] == "PENDING"
    assert state["q10"] == "NOT_VERIFIED"
    assert state["production"] == "NO-GO"

    result = verify_evidence_bundle(evidence_dir=evidence, output_dir=output)
    assert result["result"] == "PASS"
    assert result["system_signature"]["status"] == "CRYPTOGRAPHICALLY_VERIFIED"


def test_internal_ed25519_signature_verifies_without_public_log_and_stays_fail_closed(
    tmp_path: Path,
) -> None:
    evidence, output = _build(tmp_path)
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    private_key.write_text("PRIVATE\n", encoding="utf-8")
    public_key.write_text("PUBLIC\n", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "-sign" in command:
            output_index = command.index("-out") + 1
            Path(command[output_index]).write_bytes(b"signature")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    signed = sign_and_verify_ed25519(
        manifest_path=output / "evidence-signing-manifest.json",
        private_key_path=private_key,
        public_key_path=public_key,
        signature_path=output / "evidence-signing.ed25519.sig",
        openssl_path="/fake/openssl",
        runner=runner,
    )
    state = record_system_signature(
        output_dir=output,
        provider="openssl-ed25519-internal",
        bundle_filename=signed.signature_path.name,
        signer_identity=signed.signer_identity,
        verified_at="2026-09-04T00:02:00+00:00",
    )

    assert len(calls) == 2
    assert "-sign" in calls[0]
    assert "-verify" in calls[1]
    assert state["system_signature"]["status"] == "CRYPTOGRAPHICALLY_VERIFIED"
    assert state["system_signature"]["provider"] == "openssl-ed25519-internal"
    assert state["independent_human_review"]["status"] == "PENDING"
    assert state["owner_signoff"]["status"] == "PENDING"
    assert state["q10"] == "NOT_VERIFIED"
    assert state["production"] == "NO-GO"

    result = verify_evidence_bundle(evidence_dir=evidence, output_dir=output)
    assert result["result"] == "PASS"
