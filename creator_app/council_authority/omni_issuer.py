from __future__ import annotations

import base64
import contextlib
import json
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from creator_app.agnes.execution.omni import (
    AgentIdentity,
    CapabilityLease,
    EvidenceLevel,
    OMNIExecutionContext,
    PreExecutionRiskVerdict,
    RiskDecision,
)
from creator_app.agnes.execution.omni_provider import execution_binding_sha256
from creator_app.agnes.execution.request import SkillExecutionRequest


class OmniIssuanceDenied(PermissionError):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if _b64(raw) != value:
        raise ValueError("non-canonical base64url")
    return raw


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True, slots=True)
class OmniCapabilityRule:
    skill_id: str
    capability_id: str
    tool_id: str
    target_id: str
    environments: tuple[str, ...] = ("development", "test", "staging")
    risk: EvidenceLevel = EvidenceLevel.E1
    evidence_required: bool = True


class SQLiteOmniIssuerStore:
    """Durable leases and one-use execution claims; shared safely across processes."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("OMNI issuer store must be persistent")
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.database_path, timeout=30) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS omni_leases (
                    lease_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL,
                    expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS omni_issued_executions (
                    execution_id TEXT PRIMARY KEY, binding_sha256 TEXT NOT NULL,
                    lease_id TEXT NOT NULL REFERENCES omni_leases(lease_id),
                    expires_at REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
                );
            """)
        with contextlib.suppress(OSError):
            path.chmod(0o600)

    def register(
        self, execution_id: str, binding: str, lease_id: str, agent_id: str, expires: float
    ) -> None:
        db = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO omni_leases VALUES(?,?,?,0)", (lease_id, agent_id, expires))
            db.execute(
                "INSERT INTO omni_issued_executions VALUES(?,?,?,?,0)",
                (execution_id, binding, lease_id, expires),
            )
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def is_revoked(self, lease_id: str) -> bool:
        with sqlite3.connect(self.database_path, timeout=30) as db:
            row = db.execute(
                "SELECT revoked,expires_at FROM omni_leases WHERE lease_id=?", (lease_id,)
            ).fetchone()
        return row is None or bool(row[0]) or float(row[1]) <= time.time()

    def revoke(self, lease_id: str) -> bool:
        with sqlite3.connect(self.database_path, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("UPDATE omni_leases SET revoked=1 WHERE lease_id=?", (lease_id,))
            db.execute("COMMIT")
            return cur.rowcount == 1

    def consume(self, execution_id: str, binding: str, lease_id: str) -> bool:
        db = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT e.binding_sha256,e.lease_id,e.expires_at,e.consumed,l.revoked,l.expires_at "
                "FROM omni_issued_executions e JOIN omni_leases l ON l.lease_id=e.lease_id "
                "WHERE e.execution_id=?",
                (execution_id,),
            ).fetchone()
            ok = bool(
                row
                and row[0] == binding
                and row[1] == lease_id
                and row[2] > time.time()
                and not row[3]
                and not row[4]
                and row[5] > time.time()
            )
            if not ok:
                db.execute("ROLLBACK")
                return False
            cur = db.execute(
                "UPDATE omni_issued_executions SET consumed=1 WHERE execution_id=? AND consumed=0",
                (execution_id,),
            )
            if cur.rowcount != 1:
                db.execute("ROLLBACK")
                return False
            db.execute("COMMIT")
            return True
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()


class Ed25519OmniIssuer:
    """Issuer core; keep its private key isolated in a dedicated authority process."""

    def __init__(
        self,
        *,
        private_key: Ed25519PrivateKey,
        store: SQLiteOmniIssuerStore,
        issuer_id: str,
        agent_id: str,
        model_id: str,
        policy_id: str,
        rules: Iterable[OmniCapabilityRule],
        runtime_id: str,
        verifier_id: str,
        lease_ttl_seconds: int = 60,
        evidence_verifier: Callable[[SkillExecutionRequest, OMNIExecutionContext], bool]
        | None = None,
        approval_verifier: Callable[[SkillExecutionRequest], bool] | None = None,
    ) -> None:
        if not all((issuer_id, agent_id, model_id, policy_id, runtime_id, verifier_id)):
            raise ValueError("issuer, identity, policy, runtime, and verifier IDs are required")
        if not 1 <= lease_ttl_seconds <= 300:
            raise ValueError("lease TTL must be between 1 and 300 seconds")
        self.private_key, self.public_key, self.store = private_key, private_key.public_key(), store
        self.issuer_id, self.agent_id, self.model_id, self.policy_id = (
            issuer_id,
            agent_id,
            model_id,
            policy_id,
        )
        self.rules, self.runtime_id, self.verifier_id = tuple(rules), runtime_id, verifier_id
        self.lease_ttl_seconds = lease_ttl_seconds
        self.evidence_verifier, self.approval_verifier = evidence_verifier, approval_verifier

    def _rule(self, request: SkillExecutionRequest) -> OmniCapabilityRule:
        tool, target = request.plan_step.get("tool_id"), request.plan_step.get("target_id")
        for rule in self.rules:
            if (
                rule.skill_id == request.skill_id
                and rule.capability_id in request.granted_capabilities
                and rule.tool_id == tool
                and rule.target_id == target
                and request.environment in rule.environments
                and (request.environment != "production" or rule.risk is EvidenceLevel.E0)
            ):
                return rule
        raise OmniIssuanceDenied("no_matching_omni_issuance_policy")

    def issue_context(self, request: SkillExecutionRequest) -> OMNIExecutionContext:
        rule = self._rule(request)
        if request.requires_approval:
            if not request.approval_id or self.approval_verifier is None:
                raise OmniIssuanceDenied("approval_verification_unavailable")
            if not self.approval_verifier(request):
                raise OmniIssuanceDenied("approval_invalid")
        now = time.time()
        lease_id, expires = str(uuid.uuid4()), now + self.lease_ttl_seconds
        context = OMNIExecutionContext(
            identity=AgentIdentity(
                self.agent_id, self.model_id, self.issuer_id, "ed25519:" + self.issuer_id
            ),
            capability_id=rule.capability_id,
            lease=CapabilityLease(lease_id, self.agent_id, (rule.capability_id,), now, expires),
            policy_id=self.policy_id,
            risk_verdict=PreExecutionRiskVerdict(
                str(uuid.uuid4()),
                request.execution_id,
                self.agent_id,
                rule.capability_id,
                self.policy_id,
                RiskDecision.ALLOW,
                rule.risk,
                "policy-bound-target",
                "policy-defined",
                "policy-defined",
                rule.risk is not EvidenceLevel.E0,
            ),
            tool_id=rule.tool_id,
            target_id=rule.target_id,
            runtime_id=self.runtime_id,
            verifier_id=self.verifier_id,
            evidence_required=rule.evidence_required,
            intent_id=request.correlation_id,
        )
        context.validate(request)
        binding = execution_binding_sha256(request, context)
        claims = {
            "iss": self.issuer_id,
            "sub": self.agent_id,
            "execution_id": request.execution_id,
            "lease_id": lease_id,
            "binding_sha256": binding,
            "iat": int(now),
            "exp": int(expires),
        }
        proof = _b64(_canonical(claims)) + "." + _b64(self.private_key.sign(_canonical(claims)))
        context = replace(context, proof=proof)
        self.store.register(request.execution_id, binding, lease_id, self.agent_id, expires)
        return context

    def verify_context_proof(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool:
        try:
            body, sig = context.proof.split(".", 1)
            claims = json.loads(_unb64(body))
            self.public_key.verify(_unb64(sig), _canonical(claims))
            now = int(time.time())
            return bool(
                claims.get("iss") == self.issuer_id
                and claims.get("sub") == context.identity.agent_id
                and claims.get("execution_id") == request.execution_id
                and claims.get("lease_id") == context.lease.lease_id
                and claims.get("binding_sha256") == execution_binding_sha256(request, context)
                and int(claims.get("exp", 0)) > now
                and int(claims.get("iat", 0)) <= now + 5
                and context.identity.issuer == self.issuer_id
            )
        except (ValueError, TypeError, KeyError, InvalidSignature, json.JSONDecodeError):
            return False

    def verify_evidence(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool:
        if not context.evidence_required:
            return True
        if self.evidence_verifier is None:
            return False
        try:
            return bool(self.evidence_verifier(request, context))
        except Exception:
            return False

    def is_lease_revoked(self, lease_id: str) -> bool:
        return self.store.is_revoked(lease_id)

    def consume_execution(self, execution_id: str, binding_sha256: str, lease_id: str) -> bool:
        return self.store.consume(execution_id, binding_sha256, lease_id)

    def revoke_lease(self, lease_id: str) -> bool:
        return self.store.revoke(lease_id)


class Ed25519OmniProofVerifier:
    """AGNES-side proof verifier; holds only the public key."""

    def __init__(self, public_key: Ed25519PublicKey, *, issuer_id: str) -> None:
        self.public_key, self.issuer_id = public_key, issuer_id

    def verify(self, request: SkillExecutionRequest, context: OMNIExecutionContext) -> bool:
        try:
            body, sig = context.proof.split(".", 1)
            claims = json.loads(_unb64(body))
            self.public_key.verify(_unb64(sig), _canonical(claims))
            return bool(
                claims.get("iss") == self.issuer_id
                and claims.get("sub") == context.identity.agent_id
                and context.identity.issuer == self.issuer_id
                and claims.get("execution_id") == request.execution_id
                and claims.get("lease_id") == context.lease.lease_id
                and claims.get("binding_sha256") == execution_binding_sha256(request, context)
                and int(claims.get("exp", 0)) > int(time.time())
            )
        except (ValueError, TypeError, KeyError, InvalidSignature, json.JSONDecodeError):
            return False
