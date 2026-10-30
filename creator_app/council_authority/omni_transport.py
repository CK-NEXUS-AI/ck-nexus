"""Authenticated loopback HTTP transport for a separately operated OMNI issuer."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from creator_app.agnes.execution.omni import (
    AgentIdentity,
    CapabilityLease,
    DelegationContext,
    EvidenceLevel,
    OMNIExecutionContext,
    PreExecutionRiskVerdict,
    RiskDecision,
)
from creator_app.agnes.execution.omni_provider import (
    IndependentOmniAuthority,
)
from creator_app.agnes.execution.request import (
    CredentialRequirement,
    ExecutorType,
    SkillExecutionRequest,
)
from creator_app.council_authority.identity import IdentityError, IdentityVerifier
from creator_app.council_authority.omni_issuer import (
    Ed25519OmniIssuer,
    Ed25519OmniProofVerifier,
)


def request_to_wire(req: SkillExecutionRequest) -> dict[str, Any]:
    from creator_app.agnes.execution.request import thaw

    return {
        "execution_id": req.execution_id,
        "correlation_id": req.correlation_id,
        "skill_id": req.skill_id,
        "skill_version": req.skill_version,
        "executor": req.executor.value,
        "goal": req.goal,
        "plan_step": thaw(req.plan_step),
        "inputs": thaw(req.inputs),
        "tenant_id": req.tenant_id,
        "actor_id": req.actor_id,
        "environment": req.environment,
        "policy_version": req.policy_version,
        "workspace_id": req.workspace_id,
        "baseline_commit": req.baseline_commit,
        "requires_approval": req.requires_approval,
        "approval_id": req.approval_id,
        "timeout_seconds": req.timeout_seconds,
        "idempotency_key": req.idempotency_key,
        "allowlist_paths": list(req.allowlist_paths),
        "granted_capabilities": list(req.granted_capabilities),
        "credential_requirements": [
            {"credential_id": c.credential_id, "consumer": c.consumer, "purpose": c.purpose}
            for c in req.credential_requirements
        ],
    }


def request_from_wire(data: dict[str, Any]) -> SkillExecutionRequest:
    allowed = {
        "execution_id",
        "correlation_id",
        "skill_id",
        "skill_version",
        "executor",
        "goal",
        "plan_step",
        "inputs",
        "tenant_id",
        "actor_id",
        "environment",
        "policy_version",
        "workspace_id",
        "baseline_commit",
        "requires_approval",
        "approval_id",
        "timeout_seconds",
        "idempotency_key",
        "allowlist_paths",
        "granted_capabilities",
        "credential_requirements",
    }
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("invalid execution request schema")
    creds = data.get("credential_requirements", [])
    if not isinstance(creds, list) or any(
        not isinstance(c, dict) or set(c) != {"credential_id", "consumer", "purpose"} for c in creds
    ):
        raise ValueError("invalid credential requirement schema")
    return SkillExecutionRequest(
        execution_id=data["execution_id"],
        correlation_id=data["correlation_id"],
        skill_id=data["skill_id"],
        skill_version=data["skill_version"],
        executor=ExecutorType(data["executor"]),
        goal=data["goal"],
        plan_step=data.get("plan_step", {}),
        inputs=data.get("inputs", {}),
        tenant_id=data.get("tenant_id", "default"),
        actor_id=data.get("actor_id", "system"),
        environment=data.get("environment", "development"),
        policy_version=data.get("policy_version", "r14-phase1"),
        workspace_id=data.get("workspace_id"),
        baseline_commit=data.get("baseline_commit"),
        requires_approval=bool(data.get("requires_approval", False)),
        approval_id=data.get("approval_id"),
        timeout_seconds=int(data.get("timeout_seconds", 300)),
        idempotency_key=data.get("idempotency_key"),
        allowlist_paths=tuple(data.get("allowlist_paths", [])),
        granted_capabilities=tuple(data.get("granted_capabilities", [])),
        credential_requirements=tuple(CredentialRequirement(**c) for c in creds),
    )


def context_to_wire(ctx: OMNIExecutionContext) -> dict[str, Any]:
    return {
        "identity": {
            "agent_id": ctx.identity.agent_id,
            "model_id": ctx.identity.model_id,
            "issuer": ctx.identity.issuer,
            "identity_ref": ctx.identity.identity_ref,
        },
        "capability_id": ctx.capability_id,
        "lease": {
            "lease_id": ctx.lease.lease_id,
            "agent_id": ctx.lease.agent_id,
            "capabilities": list(ctx.lease.capabilities),
            "issued_at": ctx.lease.issued_at,
            "expires_at": ctx.lease.expires_at,
            "revocation_ref": ctx.lease.revocation_ref,
        },
        "policy_id": ctx.policy_id,
        "risk_verdict": {
            "risk_verdict_id": ctx.risk_verdict.risk_verdict_id,
            "execution_id": ctx.risk_verdict.execution_id,
            "agent_id": ctx.risk_verdict.agent_id,
            "capability_id": ctx.risk_verdict.capability_id,
            "policy_id": ctx.risk_verdict.policy_id,
            "decision": ctx.risk_verdict.decision.value,
            "risk": ctx.risk_verdict.risk.value,
            "blast_radius": ctx.risk_verdict.blast_radius,
            "reversibility": ctx.risk_verdict.reversibility,
            "data_sensitivity": ctx.risk_verdict.data_sensitivity,
            "external_side_effect": ctx.risk_verdict.external_side_effect,
        },
        "tool_id": ctx.tool_id,
        "target_id": ctx.target_id,
        "runtime_id": ctx.runtime_id,
        "verifier_id": ctx.verifier_id,
        "evidence_required": ctx.evidence_required,
        "intent_id": ctx.intent_id,
        "delegation": (
            {
                "parent_execution_id": ctx.delegation.parent_execution_id,
                "parent_agent_id": ctx.delegation.parent_agent_id,
                "delegated_capabilities": list(ctx.delegation.delegated_capabilities),
                "child_agent_id": ctx.delegation.child_agent_id,
            }
            if ctx.delegation
            else None
        ),
        "proof": ctx.proof,
    }


def context_from_wire(data: dict[str, Any]) -> OMNIExecutionContext:
    allowed = {
        "identity",
        "capability_id",
        "lease",
        "policy_id",
        "risk_verdict",
        "tool_id",
        "target_id",
        "runtime_id",
        "verifier_id",
        "evidence_required",
        "intent_id",
        "delegation",
        "proof",
    }
    if not isinstance(data, dict) or set(data) != allowed:
        raise ValueError("invalid OMNI context schema")
    ident, lease, risk = data["identity"], data["lease"], data["risk_verdict"]
    deleg = data["delegation"]
    return OMNIExecutionContext(
        identity=AgentIdentity(**ident),
        capability_id=data["capability_id"],
        lease=CapabilityLease(
            lease_id=lease["lease_id"],
            agent_id=lease["agent_id"],
            capabilities=tuple(lease["capabilities"]),
            issued_at=float(lease["issued_at"]),
            expires_at=float(lease["expires_at"]),
            revocation_ref=lease.get("revocation_ref"),
        ),
        policy_id=data["policy_id"],
        risk_verdict=PreExecutionRiskVerdict(
            risk_verdict_id=risk["risk_verdict_id"],
            execution_id=risk["execution_id"],
            agent_id=risk["agent_id"],
            capability_id=risk["capability_id"],
            policy_id=risk["policy_id"],
            decision=RiskDecision(risk["decision"]),
            risk=EvidenceLevel(risk["risk"]),
            blast_radius=risk["blast_radius"],
            reversibility=risk["reversibility"],
            data_sensitivity=risk["data_sensitivity"],
            external_side_effect=bool(risk["external_side_effect"]),
        ),
        tool_id=data["tool_id"],
        target_id=data["target_id"],
        runtime_id=data["runtime_id"],
        verifier_id=data["verifier_id"],
        evidence_required=data["evidence_required"],
        intent_id=data["intent_id"],
        delegation=(
            DelegationContext(
                deleg["parent_execution_id"],
                deleg["parent_agent_id"],
                tuple(deleg["delegated_capabilities"]),
                deleg["child_agent_id"],
            )
            if deleg
            else None
        ),
        proof=data["proof"],
    )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_request(request: urllib.request.Request, timeout: float):
    opener = urllib.request.build_opener(
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)


class OmniIssuerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        address: tuple[str, int],
        issuer: Ed25519OmniIssuer,
        identity_verifier: IdentityVerifier,
        *,
        allowed_service_id: str,
    ):
        if address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("OMNI issuer HTTP server must bind to loopback")
        self.issuer = issuer
        self.identity_verifier = identity_verifier
        self.allowed_service_id = allowed_service_id
        super().__init__(address, _IssuerHandler)


class _IssuerHandler(BaseHTTPRequestHandler):
    server: OmniIssuerHTTPServer
    protocol_version = "HTTP/1.1"
    max_body = 1024 * 1024

    def _reply(self, status: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(raw)))
        self.close_connection = True
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > self.max_body:
            raise ValueError("invalid request body size")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(3.0)

    def _authenticate(self) -> None:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise IdentityError("missing bearer token")
        ident = self.server.identity_verifier.verify(header[7:])
        if (
            ident.service_id != self.server.allowed_service_id
            or ident.agent_id != self.server.issuer.agent_id
        ):
            raise IdentityError("service identity denied")

    def do_POST(self) -> None:
        try:
            self._authenticate()
            body = self._body()
            if self.path == "/v1/omni/issue":
                req = request_from_wire(body["request"])
                ctx = self.server.issuer.issue_context(req)
                self._reply(200, {"context": context_to_wire(ctx)})
                return
            if self.path == "/v1/omni/evidence/verify":
                req = request_from_wire(body["request"])
                ctx = context_from_wire(body["context"])
                if not self.server.issuer.verify_context_proof(req, ctx):
                    self._reply(403, {"error": "INVALID_CONTEXT_PROOF"})
                    return
                self._reply(200, {"valid": self.server.issuer.verify_evidence(req, ctx)})
                return
            if self.path == "/v1/omni/consume":
                ok = self.server.issuer.consume_execution(
                    str(body["execution_id"]), str(body["binding_sha256"]), str(body["lease_id"])
                )
                self._reply(200 if ok else 403, {"consumed": ok})
                return
            if self.path == "/v1/omni/revoked":
                ok = self.server.issuer.is_lease_revoked(str(body["lease_id"]))
                self._reply(200, {"revoked": ok})
                return
            self._reply(404, {"error": "NOT_FOUND"})
        except IdentityError:
            self._reply(401, {"error": "IDENTITY_DENIED"})
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            self._reply(400, {"error": "BAD_REQUEST"})
        except Exception:
            self._reply(503, {"error": "AUTHORITY_UNAVAILABLE"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


class HttpIndependentOmniAuthority(IndependentOmniAuthority):
    """AGNES-side client; holds the public key and a short-lived service token only."""

    def __init__(
        self,
        base_url: str,
        *,
        service_token: str,
        public_key: Ed25519PublicKey,
        issuer_id: str,
        timeout_seconds: float = 2.0,
    ):
        try:
            parsed_url = urllib.parse.urlsplit(base_url)
            hostname = (parsed_url.hostname or "").lower().rstrip(".")
            _ = parsed_url.port
        except ValueError as exc:
            raise ValueError("issuer URL is malformed") from exc
        loopback_http = parsed_url.scheme == "http" and hostname in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        valid_https = parsed_url.scheme == "https" and bool(hostname)
        if (
            not (loopback_http or valid_https)
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("issuer URL must use loopback HTTP or credential-free HTTPS")
        if not service_token or not 0 < timeout_seconds <= 5:
            raise ValueError("service token and timeout (0–5s] are required")
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout_seconds = timeout_seconds
        self.proof_verifier = Ed25519OmniProofVerifier(public_key, issuer_id=issuer_id)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
        req = urllib.request.Request(
            self.base_url + path,
            data=raw,
            method="POST",
            headers={
                "Authorization": "Bearer " + self.service_token,
                "Content-Type": "application/json",
                "Cache-Control": "no-store",
            },
        )
        try:
            with _open_request(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise RuntimeError("OMNI authority rejected request")
                data = json.loads(response.read(1024 * 1024))
                if not isinstance(data, dict):
                    raise RuntimeError("invalid OMNI authority response")
                return data
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("OMNI authority unavailable") from exc

    def issue_context(self, request: SkillExecutionRequest) -> OMNIExecutionContext:
        data = self._post("/v1/omni/issue", {"request": request_to_wire(request)})
        return context_from_wire(data["context"])

    def verify_context_proof(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool:
        return self.proof_verifier.verify(request, context)

    def verify_evidence(
        self, request: SkillExecutionRequest, context: OMNIExecutionContext
    ) -> bool:
        return (
            self._post(
                "/v1/omni/evidence/verify",
                {
                    "request": request_to_wire(request),
                    "context": context_to_wire(context),
                },
            ).get("valid")
            is True
        )

    def is_lease_revoked(self, lease_id: str) -> bool:
        return self._post("/v1/omni/revoked", {"lease_id": lease_id}).get("revoked") is True

    def consume_execution(self, execution_id: str, binding_sha256: str, lease_id: str) -> bool:
        try:
            return (
                self._post(
                    "/v1/omni/consume",
                    {
                        "execution_id": execution_id,
                        "binding_sha256": binding_sha256,
                        "lease_id": lease_id,
                    },
                ).get("consumed")
                is True
            )
        except RuntimeError:
            return False
