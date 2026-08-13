from __future__ import annotations

import hashlib
import json
import tempfile
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
    assert a.consume_grant(ident, g, params) is True
    assert a.consume_grant(ident, g, params) is False
    out = a.enforce(
        ident,
        "council.engineering.inspect_repo",
        params,
        {"taskId": "t1", "evidenceRef": "git:repo@abc"},
    )
    assert a.consume_grant(ident, out["executionGrant"], {"repo": "other"}) is False
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
    out = arb.resolve("d", "security", [p], high_risk=True)
    assert out["status"] != "BLOCKED_SAFETY_VETO"
    s.seed_evidence(ref="gate:r23", kind="artifact", digest="b" * 64, task_id=None, quality=1)
    veto = Proposal("COUNCIL-03", "do-not-ship", ["gate:r23"], 0.9, "high", "gate failed", True)
    out = arb.resolve("d2", "security", [p, veto], high_risk=True)
    assert out["status"] == "BLOCKED_SAFETY_VETO"
    assert out["vetoBy"] == "COUNCIL-03"
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
