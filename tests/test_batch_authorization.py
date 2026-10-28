from __future__ import annotations

import time

import pytest

from creator_app.control_plane.batch_authorization import (
    AuthorizationStore,
    PermissionRequest,
    evaluate_authorization,
)


def test_batch_grant_authorizes_multiple_scopes_and_targets(tmp_path) -> None:
    store = AuthorizationStore(tmp_path / "authorization.sqlite3")
    grant = store.create_grant(
        grant_id="grant-dev-1",
        permissions=["repo.read", "repo.write", "tests.run"],
        targets=["repo:CK-NEXUS-AI/ck-nexus", "vps:ck-nexus"],
        approved_by="human-session",
        ttl_seconds=3600,
    )

    assert grant["permissions"] == ["repo.read", "repo.write", "tests.run"]
    assert evaluate_authorization(
        store,
        PermissionRequest(permission="repo.write", target="repo:CK-NEXUS-AI/ck-nexus"),
    ).allowed
    assert evaluate_authorization(
        store, PermissionRequest(permission="tests.run", target="vps:ck-nexus")
    ).allowed


def test_batch_grant_denies_unlisted_permission_and_target(tmp_path) -> None:
    store = AuthorizationStore(tmp_path / "authorization.sqlite3")
    store.create_grant(
        grant_id="grant-dev-2",
        permissions=["repo.read"],
        targets=["repo:CK-NEXUS-AI/ck-nexus"],
        approved_by="human-session",
        ttl_seconds=3600,
    )

    assert not evaluate_authorization(
        store, PermissionRequest(permission="repo.delete", target="repo:CK-NEXUS-AI/ck-nexus")
    ).allowed
    assert not evaluate_authorization(
        store, PermissionRequest(permission="repo.read", target="vps:other")
    ).allowed


def test_grant_expires_and_revocation_is_persistent(tmp_path) -> None:
    path = tmp_path / "authorization.sqlite3"
    store = AuthorizationStore(path)
    store.create_grant(
        grant_id="grant-expiring",
        permissions=["repo.read"],
        targets=["repo:demo"],
        approved_by="human-session",
        ttl_seconds=1,
    )
    time.sleep(1.05)
    assert not evaluate_authorization(
        store, PermissionRequest(permission="repo.read", target="repo:demo")
    ).allowed

    store.create_grant(
        grant_id="grant-revoked",
        permissions=["repo.read"],
        targets=["repo:demo"],
        approved_by="human-session",
        ttl_seconds=3600,
    )
    store.revoke("grant-revoked", revoked_by="human-session")
    reopened = AuthorizationStore(path)
    assert not evaluate_authorization(
        reopened, PermissionRequest(permission="repo.read", target="repo:demo")
    ).allowed


def test_batch_grant_is_atomic_and_rejects_wildcards_and_invalid_ttl(tmp_path) -> None:
    store = AuthorizationStore(tmp_path / "authorization.sqlite3")
    with pytest.raises(ValueError):
        store.create_grant(
            grant_id="grant-wildcard",
            permissions=["*"],
            targets=["*"],
            approved_by="human-session",
            ttl_seconds=3600,
        )
    with pytest.raises(ValueError):
        store.create_grant(
            grant_id="grant-invalid-ttl",
            permissions=["repo.read"],
            targets=["repo:demo"],
            approved_by="human-session",
            ttl_seconds=0,
        )
    assert store.list_grants() == []


def test_high_impact_request_requires_separate_explicit_approval(tmp_path) -> None:
    store = AuthorizationStore(tmp_path / "authorization.sqlite3")
    store.create_grant(
        grant_id="grant-safe",
        permissions=["repo.read", "repo.write", "repo.delete"],
        targets=["repo:demo"],
        approved_by="human-session",
        ttl_seconds=3600,
    )
    decision = evaluate_authorization(
        store,
        PermissionRequest(
            permission="repo.delete",
            target="repo:demo",
            high_impact=True,
        ),
    )
    assert not decision.allowed
    assert decision.reason == "high_impact_requires_explicit_approval"

    store.create_grant(
        grant_id="grant-high-impact",
        permissions=["repo.write", "repo.delete"],
        targets=["repo:demo"],
        approved_by="human-session",
        ttl_seconds=3600,
        high_impact_permissions=["repo.delete"],
    )
    assert evaluate_authorization(
        store,
        PermissionRequest(permission="repo.delete", target="repo:demo", high_impact=True),
    ).allowed
    assert not evaluate_authorization(
        store,
        PermissionRequest(permission="repo.write", target="repo:demo", high_impact=True),
    ).allowed
