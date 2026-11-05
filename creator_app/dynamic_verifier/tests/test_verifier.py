"""Tests for CK-NEXUS isolated dynamic patch verification."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from creator_app.dynamic_verifier import verifier as dynamic_module
from creator_app.dynamic_verifier.verifier import (
    DynamicVerificationBlocked,
    DynamicVerificationInput,
    DynamicVerifierLimits,
    IsolatedDynamicVerifier,
    _verifier_container_command,
)
from creator_app.patch_verifier import verifier as static_module

_EXECUTION_ID = "devexec-" + "a" * 20
_IMAGE = (
    "ghcr.io/ck-nexus-ai/ck-nexus-verifier-python@sha256:"
    "fee488944575873dd7e1e42e355f5272953cba8bf6342e9ea043f8e257c1d60c"
)
_UNTRUSTED_IMAGE = "ghcr.io/example/unreviewed@sha256:" + "b" * 64
_PATCH = (
    b"diff --git a/example.txt b/example.txt\n"
    b"--- a/example.txt\n"
    b"+++ b/example.txt\n"
    b"@@ -1 +1 @@\n"
    b"-old\n"
    b"+new\n"
)


def _git(repo: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
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
    _git(repo, "add", "example.txt")
    _git(
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
    result = _git(repo, "rev-parse", "HEAD", capture=True)
    return repo, result.stdout.decode().strip()


def _non_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dynamic_module.os, "getuid", lambda: 1000)
    monkeypatch.setattr(dynamic_module.os, "getgid", lambda: 1000)
    monkeypatch.setattr(static_module.os, "getuid", lambda: 1000)


def test_verifier_command_enforces_dynamic_isolation(tmp_path: Path) -> None:
    command = _verifier_container_command(
        engine="docker",
        worktree=tmp_path / "worktree",
        verifier_image=_IMAGE,
        profile="python_quality",
        execution_id=_EXECUTION_ID,
        uid=1000,
        gid=1000,
        limits=DynamicVerifierLimits(),
    )
    assert "--pull=never" in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--user=1000:1000" in command
    assert command[-1] == "/cknexus/verify"
    assert all("docker.sock" not in item for item in command)
    assert "--privileged" not in command


def test_dynamic_verify_rechecks_static_and_uses_disposable_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    monkeypatch.setattr(
        IsolatedDynamicVerifier,
        "_run_verifier_container",
        staticmethod(lambda request, worktree: 0),
    )
    digest = hashlib.sha256(_PATCH).hexdigest()
    result = IsolatedDynamicVerifier().verify(
        DynamicVerificationInput(
            patch=_PATCH,
            patch_digest=digest,
            execution_id=_EXECUTION_ID,
            assistant_id="aider",
            repository_path=repo,
            source_sha=source_sha,
            verifier_image=_IMAGE,
        )
    )
    assert result.state == "VERIFIED_DYNAMIC"
    assert result.release_evidence is False
    assert result.production_status == "NO-GO"
    verification = result.evidence["verification"]
    assert verification["network"] == "deny"
    assert verification["credential_forwarding"] is False
    assert verification["patched_code_executed_on_host"] is False
    assert verification["patch_applied_to_canonical_checkout"] is False
    assert verification["trusted_image_source_commit"] == (
        "942ef54229b5e46334820a94affa09ca14110820"
    )
    assert verification["trusted_image_discovery_run_id"] == 41941102071
    assert (repo / "example.txt").read_text(encoding="utf-8") == "old\n"


def test_validate_rejects_unpinned_verifier_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image="ghcr.io/spinlnw10-art/ck-nexus-verifier-python:latest",
    )
    with pytest.raises(DynamicVerificationBlocked, match="digest-pinned"):
        IsolatedDynamicVerifier._validate(request)


def test_validate_rejects_digest_pinned_but_untrusted_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=_UNTRUSTED_IMAGE,
    )
    with pytest.raises(DynamicVerificationBlocked, match="trusted registry"):
        IsolatedDynamicVerifier._validate(request)


def test_command_rejects_digest_pinned_but_untrusted_image(tmp_path: Path) -> None:
    with pytest.raises(DynamicVerificationBlocked, match="not trusted"):
        _verifier_container_command(
            engine="docker",
            worktree=tmp_path / "worktree",
            verifier_image=_UNTRUSTED_IMAGE,
            profile="python_quality",
            execution_id=_EXECUTION_ID,
            uid=1000,
            gid=1000,
            limits=DynamicVerifierLimits(),
        )


def test_validate_rejects_retired_personal_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=(
            "ghcr.io/spinlnw10-art/ck-nexus-verifier-python@sha256:"
            "f495574f3076eea84467f486ee6eb3ebb0136d7e41322429eb0bc435561ad751"
        ),
    )
    with pytest.raises(DynamicVerificationBlocked, match="trusted registry"):
        IsolatedDynamicVerifier._validate(request)


def test_validate_rejects_unapproved_container_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=_IMAGE,
        engine="bash",
    )
    with pytest.raises(DynamicVerificationBlocked, match="engine is not allowlisted"):
        IsolatedDynamicVerifier._validate(request)


def test_validate_rejects_unknown_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=_IMAGE,
        profile="arbitrary_shell",
    )
    with pytest.raises(DynamicVerificationBlocked, match="profile"):
        IsolatedDynamicVerifier._validate(request)


def test_validate_rejects_patch_digest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    _non_root(monkeypatch)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest="c" * 64,
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=_IMAGE,
    )
    with pytest.raises(DynamicVerificationBlocked, match="digest mismatch"):
        IsolatedDynamicVerifier._validate(request)


def test_validate_refuses_root_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source_sha = _repo(tmp_path)
    monkeypatch.setattr(dynamic_module.os, "getuid", lambda: 0)
    request = DynamicVerificationInput(
        patch=_PATCH,
        patch_digest=hashlib.sha256(_PATCH).hexdigest(),
        execution_id=_EXECUTION_ID,
        assistant_id="aider",
        repository_path=repo,
        source_sha=source_sha,
        verifier_image=_IMAGE,
    )
    with pytest.raises(DynamicVerificationBlocked, match="non-root host"):
        IsolatedDynamicVerifier._validate(request)
