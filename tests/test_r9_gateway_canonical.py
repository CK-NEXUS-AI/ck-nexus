from __future__ import annotations

from fastapi.testclient import TestClient

from gateway.app import GatewayDependencies, create_app
from gateway.audit import InMemoryAuditSink
from gateway.config import GatewaySettings, RateLimitPolicy, RoutePolicy
from gateway.correlation import normalize_correlation_id
from gateway.errors import GatewayError
from gateway.proxy import UpstreamResponse
from gateway.rate_limit import InMemoryTokenBucket, safe_fragment
from gateway.routing import RouteRegistry


class FakeDecoder:
    def __init__(self, permissions=("system.read",)):
        self.permissions = list(permissions)

    def decode(self, token: str, *, audience: str):
        if token == "bad":
            raise GatewayError("UNAUTHORIZED", "Invalid or expired access token.", 401)
        return {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "roles": ["owner"],
            "permissions": self.permissions,
            "iss": "ck-nexus",
            "aud": audience,
            "exp": 9_999_999_999,
            "iat": 1,
        }


class FakeProxy:
    def __init__(self):
        self.calls = []

    async def request(self, method, url, *, query, body, headers, timeout_seconds):
        self.calls.append((method, url, query, body, dict(headers), timeout_seconds))
        return UpstreamResponse(200, b'{"ok":true}')


class SharedLimiter:
    def __init__(self, inner):
        self.inner = inner

    async def consume(self, tenant_id, actor_id, route_id, policy, **kwargs):
        return await self.inner.consume(tenant_id, actor_id, route_id, policy, **kwargs)


def settings(capacity=2):
    route = RoutePolicy(
        id="system.status",
        path_prefix="/api/v1/system/status",
        methods=frozenset({"GET"}),
        upstream="creator-runtime",
        audience="creator-runtime",
        permissions=frozenset({"system.read"}),
        rate_limit_policy="read-standard",
        timeout_ms=5000,
    )
    return GatewaySettings(
        environment="test",
        jwt_public_key="test-key",
        upstreams={"creator-runtime": "http://127.0.0.1:8102"},
        route_policies=(route,),
        rate_policies={"read-standard": RateLimitPolicy("read-standard", capacity, 0.000001)},
        audit_required=True,
    )


def make_client(*, permissions=("system.read",), capacity=2):
    cfg = settings(capacity)
    state = {}
    limiter = InMemoryTokenBucket(policy_version=cfg.policy_version, shared_state=state)
    audit = InMemoryAuditSink()
    proxy = FakeProxy()
    deps = GatewayDependencies(
        settings=cfg,
        decoder=FakeDecoder(permissions),
        limiter=SharedLimiter(limiter),
        proxy=proxy,
        audit=audit,
        routes=RouteRegistry(cfg.route_policies, cfg.upstreams),
    )
    return TestClient(create_app(settings=cfg, dependencies=deps)), proxy, audit, limiter


def test_health_live_and_ready_are_public():
    client, _, _, _ = make_client()
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_gateway_proxies_only_allowlisted_route_and_emits_audit():
    client, proxy, audit, _ = make_client()
    response = client.get("/api/v1/system/status", headers={"Authorization": "Bearer ok"})
    assert response.status_code == 200
    assert proxy.calls[0][1] == "http://127.0.0.1:8102/api/v1/system/status"
    assert "authorization" not in {k.lower() for k in proxy.calls[0][4]}
    assert "cookie" not in {k.lower() for k in proxy.calls[0][4]}
    assert audit.events[0].route_id == "system.status"
    assert response.headers["X-CK-Correlation-ID"]


def test_permission_denied_before_proxy():
    client, proxy, _, _ = make_client(permissions=())
    response = client.get("/api/v1/system/status", headers={"Authorization": "Bearer ok"})
    assert response.status_code == 403
    assert proxy.calls == []


def test_unknown_route_does_not_accept_user_controlled_host():
    client, proxy, _, _ = make_client()
    response = client.get("/http://evil.example/", headers={"Authorization": "Bearer ok"})
    assert response.status_code == 404
    assert proxy.calls == []


def test_shared_budget_across_two_limiter_instances():
    cfg = settings(capacity=3)
    shared = {}
    a = InMemoryTokenBucket(policy_version=cfg.policy_version, shared_state=shared)
    b = InMemoryTokenBucket(policy_version=cfg.policy_version, shared_state=shared)
    import asyncio

    async def scenario():
        policy = cfg.rate_policies["read-standard"]
        results = []
        for index in range(5):
            limiter = a if index % 2 == 0 else b
            results.append(await limiter.consume("t", "u", "r", policy, now_ms=1000))
        return results

    decisions = asyncio.run(scenario())
    assert sum(item.allowed for item in decisions) == 3
    assert sum(not item.allowed for item in decisions) == 2


def test_rate_limit_key_fragments_are_normalized():
    assert safe_fragment("tenant/../../secret") == "tenant_.._.._secret"


def test_correlation_id_rejects_arbitrary_string():
    assert normalize_correlation_id("not-a-uuid") != "not-a-uuid"
