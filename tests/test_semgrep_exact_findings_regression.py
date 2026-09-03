from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from creator_app.agnes.execution.sandbox.workspace import SandboxWorkspaceManager
from creator_app.dynamic_verifier.verifier import (
    DynamicVerificationBlocked,
    DynamicVerifierLimits,
    _verifier_container_command,
)
from creator_app.runtime import CreatorRuntime
from creator_app.schemas import RunRequest
from services.email_gateway.repository import EmailGatewayRepository


_TRUSTED_IMAGE = (
    "ghcr.io/spinlnw10-art/ck-nexus-verifier-python@sha256:"
    "f495574f3076eea84467f486ee6eb3ebb0136d7e41322429eb0bc435561ad751"
)


def _called_attributes(function: object) -> set[str]:
    source = textwrap.dedent(inspect.getsource(function))
    tree = ast.parse(source)
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_reported_runtime_taint_location_is_prompt_serialization_not_sql() -> None:
    request = RunRequest(
        agent_id="content-strategist",
        prompt="'); DROP TABLE creator_runs; --",
        audience="test",
        platform="test",
        tone="test",
        language="English",
    )

    rendered = CreatorRuntime._build_input(request)

    assert request.prompt in rendered
    assert "Values are untrusted user data" in rendered
    assert _called_attributes(CreatorRuntime._build_input).isdisjoint(
        {"execute", "executemany", "executescript", "cursor"}
    )


def test_dynamic_verifier_rejects_command_name_injection_and_keeps_argv_boundary(
    tmp_path: Path,
) -> None:
    with pytest.raises(DynamicVerificationBlocked, match="allowlisted"):
        _verifier_container_command(
            engine="docker;touch /tmp/cknexus-pwn",
            worktree=tmp_path / "worktree",
            verifier_image=_TRUSTED_IMAGE,
            profile="python_quality",
            execution_id="devexec-test",
            uid=1000,
            gid=1000,
            limits=DynamicVerifierLimits(),
        )

    marker = "devexec-safe;touch /tmp/cknexus-pwn"
    command = _verifier_container_command(
        engine="docker",
        worktree=tmp_path / "worktree",
        verifier_image=_TRUSTED_IMAGE,
        profile="python_quality",
        execution_id=marker,
        uid=1000,
        gid=1000,
        limits=DynamicVerifierLimits(),
    )
    assert command[0] == "docker"
    assert f"--env=CKNEXUS_EXECUTION_ID={marker}" in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--privileged" not in command


def test_email_outbox_dynamic_placeholder_count_does_not_interpolate_values(
    tmp_path: Path,
) -> None:
    repo = EmailGatewayRepository(tmp_path / "email.sqlite3")
    repo.initialize()
    claim = repo.claim_message(
        mailbox="security@example.invalid",
        provider="test",
        provider_message_id="message-1",
        claimed_by="ingest-worker",
    )
    assert claim.journal_id is not None
    inserted, outbox_id = repo.enqueue_outbox(
        email_journal_id=claim.journal_id,
        action_type="notify",
        destination="destination@example.invalid",
        payload={"ok": True},
        deduplication_key="outbox-security-proof",
    )
    assert inserted is True

    hostile_worker_id = "worker'); DROP TABLE email_outbox; --"
    claimed = repo.claim_outbox_batch(worker_id=hostile_worker_id, limit=20)

    assert [item.id for item in claimed] == [outbox_id]
    with repo._connect() as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='email_outbox'"
        ).fetchone()
        row = connection.execute(
            "SELECT claimed_by FROM email_outbox WHERE id = ?",
            (outbox_id,),
        ).fetchone()
    assert table_exists is not None
    assert row is not None
    assert row["claimed_by"] == hostile_worker_id


def test_workspace_tar_extraction_uses_python_data_filter_and_post_extract_symlink_guard() -> None:
    source = inspect.getsource(SandboxWorkspaceManager.open)
    assert 'extractall(path, filter="data")' in source
    assert "self._reject_symlinks(path)" in source
