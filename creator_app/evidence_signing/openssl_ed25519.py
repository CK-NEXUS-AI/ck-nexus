from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .bundle import EvidenceBundleError


@dataclass(frozen=True, slots=True)
class Ed25519VerificationResult:
    signature_path: Path
    public_key_path: Path
    signer_identity: str
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_and_verify_ed25519(
    *,
    manifest_path: Path,
    private_key_path: Path,
    public_key_path: Path,
    signature_path: Path,
    openssl_path: str | None = None,
    runner: Runner = subprocess.run,
) -> Ed25519VerificationResult:
    """Create and immediately verify an internal Ed25519 signature.

    This provides cryptographic integrity for CK-NEXUS internal evidence without
    writing signing identity or artifact metadata to a public transparency log.
    It is not independent human review, owner sign-off, or certification.
    """

    for path, label in (
        (manifest_path, "signing manifest"),
        (private_key_path, "private signing key"),
        (public_key_path, "public signing key"),
    ):
        if not path.is_file():
            raise EvidenceBundleError(f"{label} is missing")

    executable = openssl_path or shutil.which("openssl")
    if not executable:
        raise EvidenceBundleError("openssl executable is unavailable")

    signature_path.parent.mkdir(parents=True, exist_ok=True)
    sign = _run(
        [
            executable,
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(private_key_path),
            "-in",
            str(manifest_path),
            "-out",
            str(signature_path),
        ],
        runner=runner,
    )
    if sign.returncode != 0 or not signature_path.is_file():
        raise EvidenceBundleError(f"Ed25519 signing failed: {sign.stderr.strip()}")

    verify = _run(
        [
            executable,
            "pkeyutl",
            "-verify",
            "-rawin",
            "-pubin",
            "-inkey",
            str(public_key_path),
            "-sigfile",
            str(signature_path),
            "-in",
            str(manifest_path),
        ],
        runner=runner,
    )
    if verify.returncode != 0:
        raise EvidenceBundleError(f"Ed25519 verification failed: {verify.stderr.strip()}")

    signer_identity = f"sha256:{_sha256_file(public_key_path)}"
    return Ed25519VerificationResult(
        signature_path=signature_path,
        public_key_path=public_key_path,
        signer_identity=signer_identity,
        sign_stdout=sign.stdout,
        verify_stdout=verify.stdout,
    )
