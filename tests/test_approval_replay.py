from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.approval_authority import ApprovalAuthority
from creator_app.approval_replay import DurableReplayLedger


class FakeVerifier:
    def verify(self, *, challenge: str, assertion: str, actor_id: str) -> bool:
        return bool(challenge and actor_id) and assertion == "ok"


def authority(path: Path) -> ApprovalAuthority:
    return ApprovalAuthority(
        signing_key=b"k" * 32,
        verifier=FakeVerifier(),
        replay_ledger=DurableReplayLedger(path),
    )


def issue(a: ApprovalAuthority):
    c = a.create_challenge(
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
        task_id="task-1",
        tenant_id="tenant-1",
        policy_digest="p" * 64,
    )
    return a.complete_challenge(challenge_id=c.challenge_id, assertion="ok")


def redeem(a: ApprovalAuthority, token: str):
    return a.redeem(
        token,
        actor_id="user-1",
        action="provider.authorize",
        resource="provider:gemini",
        fingerprint="f" * 64,
        task_id="task-1",
        tenant_id="tenant-1",
        policy_digest="p" * 64,
    )


def test_replay_rejected_after_authority_restart(tmp_path: Path) -> None:
    path = tmp_path / "approval-replay.jsonl"
    first = authority(path)
    approval = issue(first)
    redeem(first, approval.token)

    restarted = authority(path)
    with pytest.raises(PermissionError, match="already redeemed"):
        redeem(restarted, approval.token)


def test_scope_binding_rejects_wrong_task(tmp_path: Path) -> None:
    a = authority(tmp_path / "approval-replay.jsonl")
    approval = issue(a)
    with pytest.raises(PermissionError, match="task_id mismatch"):
        a.redeem(
            approval.token,
            actor_id="user-1",
            action="provider.authorize",
            resource="provider:gemini",
            fingerprint="f" * 64,
            task_id="task-other",
            tenant_id="tenant-1",
            policy_digest="p" * 64,
        )


def test_replay_ledger_is_tamper_evident(tmp_path: Path) -> None:
    path = tmp_path / "approval-replay.jsonl"
    a = authority(path)
    approval = issue(a)
    redeem(a, approval.token)
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("user-1", "user-2", 1), encoding="utf-8")
    state = DurableReplayLedger(path).verify()
    assert state["valid"] is False
