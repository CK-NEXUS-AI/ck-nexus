from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .bundle import EvidenceBundleError


@dataclass(frozen=True, slots=True)
class CosignVerificationResult:
    bundle_path: Path
    signer_identity: str
    oidc_issuer: str
    sign_stdout: str
    verify_stdout: str


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(
    command: Sequence[str],
    *,
    runner: Runner,
) -> subprocess.CompletedProcess[str]:
    return runner(
        list(command),
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )


def sign_and_verify_keyless(
    *,
    manifest_path: Path,
    bundle_path: Path,
    signer_identity: str,
    oidc_issuer: str,
    allow_public_transparency_log: bool = False,
    cosign_path: str | None = None,
    runner: Runner = subprocess.run,
) -> CosignVerificationResult:
    """Sign one manifest with Sigstore keyless signing and verify it immediately.

    Keyless signing writes signature identity and artifact digest evidence to Sigstore's
    public transparency infrastructure. CK-NEXUS therefore requires an explicit opt-in.
    """

    if not allow_public_transparency_log:
        raise EvidenceBundleError(
            "keyless Sigstore signing requires explicit public transparency-log authorization"
        )
    if not manifest_path.is_file():
        raise EvidenceBundleError("signing manifest is missing")

    executable = cosign_path or shutil.which("cosign")
    if not executable:
        raise EvidenceBundleError("cosign executable is unavailable")

    sign = _run(
        [
            executable,
            "sign-blob",
            "--yes",
            "--bundle",
            str(bundle_path),
            str(manifest_path),
        ],
        runner=runner,
    )
    if sign.returncode != 0 or not bundle_path.is_file():
        raise EvidenceBundleError(f"cosign sign-blob failed: {sign.stderr.strip()}")

    verify = _run(
        [
            executable,
            "verify-blob",
            str(manifest_path),
            "--bundle",
            str(bundle_path),
            "--certificate-identity",
            signer_identity,
            "--certificate-oidc-issuer",
            oidc_issuer,
        ],
        runner=runner,
    )
    if verify.returncode != 0:
        raise EvidenceBundleError(f"cosign verify-blob failed: {verify.stderr.strip()}")

    return CosignVerificationResult(
        bundle_path=bundle_path,
        signer_identity=signer_identity,
        oidc_issuer=oidc_issuer,
        sign_stdout=sign.stdout,
        verify_stdout=verify.stdout,
    )
