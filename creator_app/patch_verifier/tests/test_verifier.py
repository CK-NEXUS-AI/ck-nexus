"""Tests for CK-NEXUS independent static patch verification."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from creator_app.patch_verifier import verifier as verifier_module
from creator_app.patch_verifier.verifier import (
    IndependentPatchVerifier,
    PatchRejected,
    PatchVerificationPolicy,
    _inspect_patch,
)

_EXECUTION_ID = "devexec-" + "a" * 20
_ASSISTANT_ID = "aider"
_VALID_PATCH = (
    b"diff --git a/example.txt b/example.txt\n"
    b"--- a/example.txt\n"
    b"+++ b/example.txt\n"
    b"@@ -1 +1 @@\n"
    b"-old\n"
    b"+new\n"
)


def _run_git(repo: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", str(repo)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (repo / "example.txt").write_text("old\n", encoding="utf-8")
    _run_git(repo, "add", "example.txt")
    _run_git(
        repo,
        "-c",
        "user.name=CK-NEXUS Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--no-gpg-sign",
        "-m",
        "baseline",
    )
    result = _run_git(repo, "rev-parse", "HEAD", capture=True)
    return repo, result.stdout.decode().strip()


def test_verifier_checks_exact_source_applicability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    monkeypatch.setattr(verifier_module.os, "getuid", lambda: 1000)
    digest = hashlib.sha256(_VALID_PATCH).hexdigest()

    result = IndependentPatchVerifier().verify(
        patch=_VALID_PATCH,
        expected_patch_digest=digest,
        execution_id=_EXECUTION_ID,
        assistant_id=_ASSISTANT_ID,
        repository_path=repo,
        source_sha=source_sha,
    )

    assert result.state == "VERIFIED_STATIC_APPLICABLE"
    assert result.patch_digest == digest
    assert result.changed_paths == ("example.txt",)
    assert result.release_evidence is False
    assert result.production_status == "NO-GO"
    verification = result.evidence["verification"]
    assert verification["independent_verifier"] is True
    assert verification["patched_code_executed"] is False
    assert verification["patch_applied_to_canonical_checkout"] is False


def test_verifier_rejects_patch_digest_mismatch(tmp_path: Path) -> None:
    repo, source_sha = _repo(tmp_path)
    with pytest.raises(PatchRejected, match="digest mismatch"):
        IndependentPatchVerifier().verify(
            patch=_VALID_PATCH,
            expected_patch_digest="b" * 64,
            execution_id=_EXECUTION_ID,
            assistant_id=_ASSISTANT_ID,
            repository_path=repo,
            source_sha=source_sha,
        )


def test_inspector_rejects_workflow_mutation() -> None:
    patch = (
        b"diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n"
        b"--- a/.github/workflows/ci.yml\n"
        b"+++ b/.github/workflows/ci.yml\n"
        b"@@ -1 +1 @@\n-old\n+new\n"
    )
    with pytest.raises(PatchRejected, match="forbidden path"):
        _inspect_patch(patch, PatchVerificationPolicy())


def test_inspector_rejects_environment_file() -> None:
    patch = (
        b"diff --git a/.env b/.env\n"
        b"--- a/.env\n"
        b"+++ b/.env\n"
        b"@@ -1 +1 @@\n-old\n+new\n"
    )
    with pytest.raises(PatchRejected, match="forbidden file"):
        _inspect_patch(patch, PatchVerificationPolicy())


def test_inspector_rejects_symlink_change() -> None:
    patch = (
        b"diff --git a/link b/link\n"
        b"new file mode 120000\n"
        b"--- /dev/null\n"
        b"+++ b/link\n"
        b"@@ -0,0 +1 @@\n"
        b"+target\n"
    )
    with pytest.raises(PatchRejected, match="symlink"):
        _inspect_patch(patch, PatchVerificationPolicy())


def test_inspector_rejects_binary_patch() -> None:
    patch = (
        b"diff --git a/image.bin b/image.bin\n"
        b"GIT binary patch\n"
        b"literal 1\n"
        b"AcmZQz\n"
    )
    with pytest.raises(PatchRejected, match="binary"):
        _inspect_patch(patch, PatchVerificationPolicy())


def test_inspector_rejects_path_traversal() -> None:
    patch = (
        b"diff --git a/../outside.txt b/../outside.txt\n"
        b"--- a/../outside.txt\n"
        b"+++ b/../outside.txt\n"
        b"@@ -1 +1 @@\n-old\n+new\n"
    )
    with pytest.raises(PatchRejected, match="traversal"):
        _inspect_patch(patch, PatchVerificationPolicy())


def test_verifier_refuses_root_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    monkeypatch.setattr(verifier_module.os, "getuid", lambda: 0)
    digest = hashlib.sha256(_VALID_PATCH).hexdigest()
    with pytest.raises(PatchRejected, match="non-root host"):
        IndependentPatchVerifier().verify(
            patch=_VALID_PATCH,
            expected_patch_digest=digest,
            execution_id=_EXECUTION_ID,
            assistant_id=_ASSISTANT_ID,
            repository_path=repo,
            source_sha=source_sha,
        )
