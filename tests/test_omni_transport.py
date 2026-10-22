import threading

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from creator_app.agnes.execution.omni_provider import (
    DurableExecutionReplayStore,
    OmniAuthorityUnavailable,
    OmniProviderAdapter,
)
from creator_app.council_authority.identity import IdentityVerifier
from creator_app.council_authority.omni_issuer import (
    Ed25519OmniIssuer,
    OmniCapabilityRule,
    SQLiteOmniIssuerStore,
)
from creator_app.council_authority.omni_transport import (
    HttpIndependentOmniAuthority,
    OmniIssuerHTTPServer,
)
from tests.test_omni_issuer import request


def make_issuer(tmp_path):
    return Ed25519OmniIssuer(
        private_key=Ed25519PrivateKey.generate(),
        store=SQLiteOmniIssuerStore(tmp_path / "issuer.sqlite"),
        issuer_id="transport-issuer",
        agent_id="agnes-agent",
        model_id="test-model",
        policy_id="transport-policy",
        rules=(
            OmniCapabilityRule(
                "repo.inspect",
                "code.read",
                "repo.read",
                "repo:ck-nexus",
                ("development", "test", "staging"),
                evidence_required=True,
            ),
        ),
        runtime_id="transport-runtime",
        verifier_id="transport-verifier",
        evidence_verifier=lambda _req, _ctx: True,
    )


def server_and_client(tmp_path, *, service_id="agnes-runtime"):
    issuer = make_issuer(tmp_path)
    identity_verifier = IdentityVerifier(b"i" * 32, issuer="ck-nexus-test")
    server = OmniIssuerHTTPServer(
        ("127.0.0.1", 0), issuer, identity_verifier, allowed_service_id="agnes-runtime"
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    token = identity_verifier.issue(
        service_id=service_id, agent_id="agnes-agent", role="agent", ttl_seconds=120
    )
    client = HttpIndependentOmniAuthority(
        f"http://127.0.0.1:{port}",
        service_token=token,
        public_key=issuer.public_key,
        issuer_id=issuer.issuer_id,
    )
    return issuer, server, thread, client


def close_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_issuer_boundary_works_through_production_adapter(tmp_path):
    issuer, server, thread, client = server_and_client(tmp_path)
    try:
        adapter = OmniProviderAdapter(
            client, DurableExecutionReplayStore(tmp_path / "replay.sqlite")
        )
        req = request()
        ctx = adapter(req)
        assert ctx.identity.issuer == issuer.issuer_id
        assert ctx.proof
        with pytest.raises(OmniAuthorityUnavailable):
            adapter(req)
    finally:
        close_server(server, thread)


def test_http_boundary_rejects_wrong_service_identity(tmp_path):
    _issuer, server, thread, client = server_and_client(tmp_path, service_id="untrusted-service")
    try:
        with pytest.raises(RuntimeError, match="authority unavailable"):
            client.issue_context(request("bad-service-exec"))
    finally:
        close_server(server, thread)


def test_http_server_refuses_non_loopback_bind(tmp_path):
    issuer = make_issuer(tmp_path)
    verifier = IdentityVerifier(b"i" * 32)
    with pytest.raises(ValueError, match="loopback"):
        OmniIssuerHTTPServer(("0.0.0.0", 0), issuer, verifier, allowed_service_id="agnes-runtime")


def test_http_boundary_rejects_agent_identity_mismatch(tmp_path):
    _issuer, server, thread, client = server_and_client(tmp_path, service_id="agnes-runtime")
    try:
        verifier = server.identity_verifier
        token = verifier.issue(
            service_id="agnes-runtime", agent_id="different-agent", role="agent", ttl_seconds=120
        )
        bad_client = HttpIndependentOmniAuthority(
            client.base_url,
            service_token=token,
            public_key=server.issuer.public_key,
            issuer_id=server.issuer.issuer_id,
        )
        with pytest.raises(RuntimeError, match="authority unavailable"):
            bad_client.issue_context(request("bad-agent-exec"))
    finally:
        close_server(server, thread)
