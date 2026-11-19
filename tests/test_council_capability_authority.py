from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from creator_app.council_authority.arbitration import ArbitrationEngine, Proposal
from creator_app.council_authority.authority import (
    CapabilityAuthority,
    PolicyDenied,
)
from creator_app.council_authority.identity import IdentityError, IdentityVerifier
from creator_app.council_authority.storage import AuthorityStore

CONTRACT = json.loads(
    (Path(__file__).parents[1] / "contracts/capability-policy.example.json").read_text()
)


class Broker:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def check_scope(self, consumer, ref):
        return self.allowed


def make():
    d = tempfile.TemporaryDirectory()
    store = AuthorityStore(str(Path(d.name) / "a.db"))
    ids = IdentityVerifier(b"i" * 32)
    auth = CapabilityAuthority(
        CONTRACT, store=store, broker_adapter=Broker(), grant_secret=b"g" * 32
    )
    return d, store, ids, auth


def test_identity_is_derived_from_signed_token_and_tamper_fails():
    d, s, ids, a = make()
    token = ids.issue(service_id="svc", agent_id="COUNCIL-03")
    ident = ids.verify(token)
    assert ident.agent_id == "COUNCIL-03"
    with pytest.raises(IdentityError):
        ids.verify(token[:-1] + ("A" if token[-1] != "A" else "B"))
        d.cleanup()


def test_missing_or_fake_evidence_is_denied_before_execution():
    d, s, ids, a = make()
    ident = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    with pytest.raises(PolicyDenied) as e:
        a.enforce(ident, "council.engineering.inspect_repo", {"repo": "ck-nexus"}, {"taskId": "t1"})
        assert e.value.code == "EVIDENCE_INVALID"
    with pytest.raises(PolicyDenied):
        a.enforce(
            ident,
            "council.engineering.inspect_repo",
            {"repo": "ck-nexus"},
            {"taskId": "t1", "evidenceRef": "trust-me"},
        )
        d.cleanup()


def test_verified_evidence_and_params_bound_one_time_grant():
    d, s, ids, a = make()
    ident = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    digest = hashlib.sha256(b"commit").hexdigest()
    s.seed_evidence(ref="git:repo@abc", kind="git_commit", digest=digest, task_id="t1", quality=1)
    params = {"repo": "ck-nexus"}
    out = a.enforce(
        ident,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "t1", "evidenceRef": "git:repo@abc"},
    )
    g = out["executionGrant"]
    assert a.consume_grant(ident, g, params, expected_task_id="t1") is True
    assert a.consume_grant(ident, g, params, expected_task_id="t1") is False
    out = a.enforce(
        ident,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "t1", "evidenceRef": "git:repo@abc"},
    )
    assert (
        a.consume_grant(ident, out["executionGrant"], {"repo": "other"}, expected_task_id="t1")
        is False
    )
    out = a.enforce(
        ident,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "t1", "evidenceRef": "git:repo@abc"},
    )
    assert a.consume_grant(ident, out["executionGrant"], params, expected_task_id="other") is False
    assert a.consume_grant(ident, out["executionGrant"], params, expected_task_id="t1") is True
    d.cleanup()


def test_credential_denial_is_fail_closed():
    d, s, ids, a = make()
    a.broker = Broker(False)
    ident = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    s.seed_evidence(ref="git:x", kind="git_commit", digest="a" * 64, task_id="t", quality=1)
    with pytest.raises(PolicyDenied) as e:
        a.enforce(
            ident, "council.engineering.inspect_repo", {}, {"taskId": "t", "evidenceRef": "git:x"}
        )
        assert e.value.code == "CREDENTIAL_DENIED"
        d.cleanup()


def test_safety_veto_requires_authorization_and_verified_evidence():
    d, s, ids, a = make()
    arb = ArbitrationEngine(CONTRACT, s)
    p = Proposal("COUNCIL-04", "ship", [], 0.9, "high", "", True)
    out = arb.resolve("d", "security", [p], task_id="d", high_risk=True)
    assert out["status"] != "BLOCKED_SAFETY_VETO"
    s.seed_evidence(ref="gate:r23", kind="artifact", digest="b" * 64, task_id="d2", quality=1)
    veto = Proposal("COUNCIL-03", "do-not-ship", ["gate:r23"], 0.9, "high", "gate failed", True)
    out = arb.resolve("d2", "security", [p, veto], task_id="d2", high_risk=True)
    assert out["status"] == "BLOCKED_SAFETY_VETO"
    assert out["vetoBy"] == "COUNCIL-03"
    assert out["task_id"] == "d2"
    with s._db() as db:
        audit_row = db.execute("SELECT payload FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    assert json.loads(audit_row["payload"])["task_id"] == "d2"
    d.cleanup()


def test_admin_only_topup_capability():
    d, s, ids, a = make()
    agent = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    with pytest.raises(PolicyDenied):
        a.enforce(agent, "system.budget.top_up", {"taskId": "x", "amount": 5}, {"taskId": "admin"})
    owner = ids.verify(ids.issue(service_id="owner", agent_id="OWNER", role="admin"))
    out = a.enforce(
        owner, "system.budget.top_up", {"taskId": "x", "amount": 5}, {"taskId": "admin"}
    )
    assert out["approved"]
    d.cleanup()


def test_audit_hash_chain_changes_each_record():
    d, s, ids, a = make()
    r1 = s.append_audit({"x": 1})
    r2 = s.append_audit({"x": 2})
    assert r2["previous_hash"] == r1["entry_hash"]
    assert r1["entry_hash"] != r2["entry_hash"]
    d.cleanup()


def test_authority_grant_consume_is_atomic_across_store_instances_and_restart(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    db_path = tmp_path / "authority.db"
    store = AuthorityStore(str(db_path))
    ids = IdentityVerifier(b"i" * 32)
    authority = CapabilityAuthority(
        CONTRACT, store=store, broker_adapter=Broker(), grant_secret=b"g" * 32
    )
    identity = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    digest = hashlib.sha256(b"commit").hexdigest()
    store.seed_evidence(
        ref="git:repo@atomic", kind="git_commit", digest=digest, task_id="atomic", quality=1
    )
    params = {"repo": "ck-nexus"}
    out = authority.enforce(
        identity,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "atomic", "evidenceRef": "git:repo@atomic"},
    )
    grant = out["executionGrant"]

    def consume(_):
        # Each contender opens an independent AuthorityStore/connection, simulating
        # multiple workers rather than relying on the process-local RLock.
        contender_store = AuthorityStore(str(db_path))
        contender = CapabilityAuthority(
            CONTRACT, store=contender_store, broker_adapter=Broker(), grant_secret=b"g" * 32
        )
        return contender.consume_grant(identity, grant, params, expected_task_id="atomic")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(consume, range(32)))
    assert sum(results) == 1

    # Re-open the persistent DB after all workers exit; the grant remains consumed.
    reopened = AuthorityStore(str(db_path))
    restarted = CapabilityAuthority(
        CONTRACT, store=reopened, broker_adapter=Broker(), grant_secret=b"g" * 32
    )
    assert restarted.consume_grant(identity, grant, params, expected_task_id="atomic") is False


def test_authority_consume_fails_closed_when_database_is_unavailable(tmp_path):
    d, store, ids, authority = make()
    identity = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    digest = hashlib.sha256(b"commit").hexdigest()
    store.seed_evidence(
        ref="git:repo@dbfail", kind="git_commit", digest=digest, task_id="dbfail", quality=1
    )
    params = {"repo": "ck-nexus"}
    grant = authority.enforce(
        identity,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "dbfail", "evidenceRef": "git:repo@dbfail"},
    )["executionGrant"]
    # A closed database connection/path failure must raise, never return authorization.
    store.path = str(tmp_path / "missing-parent" / "authority.db")
    with pytest.raises(sqlite3.OperationalError):
        authority.consume_grant(identity, grant, params, expected_task_id="dbfail")
    d.cleanup()


def _issue_test_grant(tmp_path, *, task_id="transaction-audit", ttl_seconds=60):
    store = AuthorityStore(str(tmp_path / f"{task_id}.sqlite"))
    ids = IdentityVerifier(b"i" * 32)
    authority = CapabilityAuthority(
        CONTRACT, store=store, broker_adapter=Broker(), grant_secret=b"g" * 32
    )
    identity = ids.verify(ids.issue(service_id="svc", agent_id="COUNCIL-03"))
    digest = hashlib.sha256(task_id.encode()).hexdigest()
    store.seed_evidence(
        ref=f"git:{task_id}",
        kind="git_commit",
        digest=digest,
        task_id=task_id,
        quality=1,
    )
    params = {"repo": "ck-nexus"}
    grant = authority.enforce(
        identity,
        "council.engineering.inspect_repo",
        params,
        {"taskId": task_id, "evidenceRef": f"git:{task_id}"},
    )["executionGrant"]
    return store, identity, authority, params, grant


def test_consume_transaction_rolls_back_on_update_failure(tmp_path):
    import sqlite3

    store, identity, authority, params, grant = _issue_test_grant(tmp_path)
    with store._db() as db:
        db.execute("""
            CREATE TRIGGER reject_grant_consume BEFORE UPDATE OF used ON grants
            WHEN NEW.used = 1
            BEGIN SELECT RAISE(ABORT, 'injected update failure'); END
        """)
    with pytest.raises(sqlite3.IntegrityError, match="injected update failure"):
        authority.consume_grant(identity, grant, params, expected_task_id="transaction-audit")

    # The failed update must not leave a used row or open transaction; after
    # removing the fault, exactly one consume is still possible.
    with store._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
        assert row["used"] == 0
        db.execute("DROP TRIGGER reject_grant_consume")
    assert (
        authority.consume_grant(identity, grant, params, expected_task_id="transaction-audit")
        is True
    )
    assert (
        authority.consume_grant(identity, grant, params, expected_task_id="transaction-audit")
        is False
    )


def test_expired_grant_is_rejected_inside_consume_transaction(tmp_path):
    store, identity, authority, params, grant = _issue_test_grant(tmp_path, task_id="expired-audit")
    with store._db() as db:
        db.execute(
            "UPDATE grants SET expires_at=? WHERE grant_id=?",
            (int(time.time()) - 1, grant["grant_id"]),
        )
    assert (
        authority.consume_grant(identity, grant, params, expected_task_id="expired-audit") is False
    )
    with store._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
        assert row["used"] == 0


def test_uncommitted_consume_is_rolled_back_after_process_crash(tmp_path):
    import subprocess
    import sys

    store, identity, authority, params, grant = _issue_test_grant(tmp_path, task_id="crash-audit")
    script = (
        "import os, sqlite3, sys; "
        "db=sqlite3.connect(sys.argv[1], isolation_level=None); "
        "db.execute('PRAGMA busy_timeout=2000'); "
        "db.execute('BEGIN IMMEDIATE'); "
        "db.execute('UPDATE grants SET used=1 WHERE grant_id=?',(sys.argv[2],)); "
        "print('UNCOMMITTED_WRITE', flush=True); os._exit(23)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script, store.path, grant["grant_id"]],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 23
    assert "UNCOMMITTED_WRITE" in proc.stdout
    # Reopening after abrupt process exit must recover the uncommitted update.
    with store._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
        assert row["used"] == 0
    assert authority.consume_grant(identity, grant, params, expected_task_id="crash-audit") is True
    assert authority.consume_grant(identity, grant, params, expected_task_id="crash-audit") is False


def test_sqlite_busy_fails_closed_without_consuming_grant(tmp_path, monkeypatch):
    import sqlite3

    store, identity, authority, params, grant = _issue_test_grant(tmp_path, task_id="busy-audit")
    lock = sqlite3.connect(store.path, timeout=1, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    original_db = store._db

    def zero_timeout_connection():
        db = sqlite3.connect(store.path, timeout=0, isolation_level=None)
        db.execute("PRAGMA busy_timeout=0")
        db.execute("PRAGMA synchronous=FULL")
        db.row_factory = sqlite3.Row
        return db

    monkeypatch.setattr(store, "_db", zero_timeout_connection)
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            authority.consume_grant(identity, grant, params, expected_task_id="busy-audit")
    finally:
        lock.execute("ROLLBACK")
        lock.close()
        monkeypatch.setattr(store, "_db", original_db)

    with store._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
        assert row["used"] == 0
    assert authority.consume_grant(identity, grant, params, expected_task_id="busy-audit") is True
    assert authority.consume_grant(identity, grant, params, expected_task_id="busy-audit") is False


def test_task_bound_evidence_rejects_unscoped_and_cross_task_records(tmp_path):
    store = AuthorityStore(str(tmp_path / "evidence-scope.sqlite"))
    digest = hashlib.sha256(b"evidence").hexdigest()
    store.seed_evidence(
        ref="evidence:global",
        kind="git_commit",
        digest=digest,
        task_id=None,
        quality=1,
    )
    store.seed_evidence(
        ref="evidence:task-a",
        kind="git_commit",
        digest=digest,
        task_id="task-a",
        quality=1,
    )
    assert store.evidence_quality(["evidence:global"], task_id="task-a") == 0
    assert store.evidence_quality(["evidence:task-a"], task_id="task-a") == 1
    assert store.evidence_quality(["evidence:task-a"], task_id="task-b") == 0


def test_grant_consumption_is_bound_to_exact_task_id(tmp_path):
    store = AuthorityStore(str(tmp_path / "grant-scope.sqlite"))
    params_hash = hashlib.sha256(b"params").hexdigest()
    grant = store.create_grant(
        agent_id="agent-a",
        capability_id="cap.read",
        params_hash=params_hash,
        task_id="task-a",
    )
    assert (
        store.consume_grant(
            grant["grant_id"],
            agent_id="agent-a",
            capability_id="cap.read",
            params_hash=params_hash,
            task_id="task-b",
        )
        is False
    )
    assert (
        store.consume_grant(
            grant["grant_id"],
            agent_id="agent-a",
            capability_id="cap.read",
            params_hash=params_hash,
            task_id="task-a",
        )
        is True
    )
    assert (
        store.consume_grant(
            grant["grant_id"],
            agent_id="agent-a",
            capability_id="cap.read",
            params_hash=params_hash,
            task_id="task-a",
        )
        is False
    )


def test_identity_rejects_null_claims_before_string_coercion():
    import base64
    import hmac

    secret = b"i" * 32
    verifier = IdentityVerifier(secret)
    payload = {
        "iss": "ck-nexus",
        "service_id": None,
        "agent_id": None,
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    signature = (
        base64.urlsafe_b64encode(hmac.new(secret, body.encode(), hashlib.sha256).digest())
        .rstrip(b"=")
        .decode()
    )
    with pytest.raises(IdentityError, match="non-empty strings"):
        verifier.verify(f"{body}.{signature}")


def test_unscoped_evidence_is_never_accepted_for_authorization(tmp_path):
    store = AuthorityStore(str(tmp_path / "authority.sqlite3"))
    store.seed_evidence(
        ref="evidence://task-a",
        kind="test",
        digest="a" * 64,
        task_id="task-a",
        quality=1.0,
    )
    assert store.evidence_quality(["evidence://task-a"]) == 0.0
    assert store.evidence_quality(["evidence://task-a"], task_id="task-b") == 0.0
    assert store.evidence_quality(["evidence://task-a"], task_id="task-a") == 1.0


def test_unscoped_grant_cannot_be_consumed(tmp_path):
    store = AuthorityStore(str(tmp_path / "authority.sqlite3"))
    grant = store.create_grant(
        agent_id="agent-a",
        capability_id="capability-a",
        params_hash="b" * 64,
        task_id=None,
    )
    assert (
        store.consume_grant(
            grant["grant_id"],
            agent_id="agent-a",
            capability_id="capability-a",
            params_hash="b" * 64,
        )
        is False
    )


def test_completion_capability_requires_explicit_task_scope():
    d, store, ids, authority = make()
    owner = ids.verify(ids.issue(service_id="owner", agent_id="OWNER", role="admin"))
    with pytest.raises(PolicyDenied) as exc:
        authority.enforce(owner, "control_plane.task.complete", {"job_id": "t"}, {})
    assert exc.value.code == "TASK_SCOPE_REQUIRED"
    d.cleanup()
