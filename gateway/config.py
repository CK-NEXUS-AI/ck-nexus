from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    id: str
    capacity: int
    refill_per_second: float
    fail_closed: bool = True

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")
        if self.refill_per_second <= 0:
            raise ValueError("refill_per_second must be > 0")


@dataclass(frozen=True, slots=True)
class RoutePolicy:
    id: str
    path_prefix: str
    methods: frozenset[str]
    upstream: str
    audience: str
    permissions: frozenset[str]
    rate_limit_policy: str
    timeout_ms: int
    cache: bool = False
    side_effect: bool = False
    fail_mode: str = "closed"
    retry: str = "none"

    def __post_init__(self) -> None:
        if not self.id or not self.path_prefix.startswith("/"):
            raise ValueError("route id/path_prefix are required")
        if not self.methods:
            raise ValueError("route methods cannot be empty")
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")
        if self.fail_mode not in {"closed", "degrade-read-only"}:
            raise ValueError("unsupported fail mode")


@dataclass(frozen=True, slots=True)
class GatewaySettings:
    environment: str = "development"
    issuer: str = "ck-nexus"
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    redis_url: str = "redis://127.0.0.1:6379/0"
    policy_version: str = "2026-08-09.1"
    request_size_limit_bytes: int = 1_048_576
    trusted_proxy_cidrs: tuple[str, ...] = ()
    upstreams: dict[str, str] = field(default_factory=dict)
    route_policies: tuple[RoutePolicy, ...] = ()
    rate_policies: dict[str, RateLimitPolicy] = field(default_factory=dict)
    audit_required: bool = True

    @classmethod
    def from_env(cls) -> GatewaySettings:
        upstreams = {
            "creator-runtime": os.environ.get("CKNEXUS_CREATOR_API_URL", "http://127.0.0.1:8102"),
            "dev-council": os.environ.get("CKNEXUS_DEVTEAM_URL", "http://127.0.0.1:8103"),
            "integrations": os.environ.get("CKNEXUS_INTEGRATIONS_URL", "http://127.0.0.1:8102"),
        }
        routes = (
            RoutePolicy(
                id="system.status",
                path_prefix="/api/v1/system/status",
                methods=frozenset({"GET"}),
                upstream="creator-runtime",
                audience="creator-runtime",
                permissions=frozenset({"system.read"}),
                rate_limit_policy="read-standard",
                timeout_ms=10_000,
                cache=True,
                fail_mode="degrade-read-only",
            ),
            RoutePolicy(
                id="creator.run",
                path_prefix="/api/v1/creator/run",
                methods=frozenset({"POST"}),
                upstream="creator-runtime",
                audience="creator-runtime",
                permissions=frozenset({"creator.run"}),
                rate_limit_policy="interactive-standard",
                timeout_ms=45_000,
                side_effect=True,
                retry="idempotency-required",
            ),
            RoutePolicy(
                id="council.consult",
                path_prefix="/api/v1/council/consult",
                methods=frozenset({"POST"}),
                upstream="dev-council",
                audience="dev-council",
                permissions=frozenset({"council.consult"}),
                rate_limit_policy="interactive-standard",
                timeout_ms=60_000,
            ),
            RoutePolicy(
                id="verification.didit.kyb.start",
                path_prefix="/api/v1/verification/didit/kyb/session",
                methods=frozenset({"POST"}),
                upstream="creator-runtime",
                audience="creator-runtime",
                permissions=frozenset({"verification.kyb.start"}),
                rate_limit_policy="interactive-standard",
                timeout_ms=15_000,
                side_effect=True,
                retry="none",
            ),
            RoutePolicy(
                id="integrations.status",
                path_prefix="/api/v1/integrations/status",
                methods=frozenset({"GET"}),
                upstream="integrations",
                audience="integrations",
                permissions=frozenset({"integrations.read"}),
                rate_limit_policy="read-standard",
                timeout_ms=10_000,
                cache=True,
                fail_mode="degrade-read-only",
            ),
        )
        return cls(
            environment=os.environ.get("CKN_ENV", "development"),
            issuer=os.environ.get("CKNEXUS_JWT_ISSUER", "ck-nexus"),
            jwt_public_key=os.environ.get("CKNEXUS_JWT_PUBLIC_KEY", ""),
            jwt_algorithm=os.environ.get("CKNEXUS_JWT_ALGORITHM", "RS256"),
            redis_url=os.environ.get("CKNEXUS_REDIS_URL", "redis://127.0.0.1:6379/0"),
            policy_version=os.environ.get("CKN_POLICY_VERSION", "2026-08-09.1"),
            upstreams=upstreams,
            route_policies=routes,
            rate_policies={
                "interactive-standard": RateLimitPolicy("interactive-standard", 60, 1.0),
                "read-standard": RateLimitPolicy("read-standard", 120, 2.0),
            },
            audit_required=os.environ.get("CKN_AUDIT_REQUIRED", "true").lower() == "true",
        )

    def validate(self) -> None:
        if self.environment == "production" and not self.jwt_public_key:
            raise ValueError("production gateway requires JWT verifier configuration")
        route_ids: set[str] = set()
        for route in self.route_policies:
            if route.id in route_ids:
                raise ValueError(f"duplicate route id: {route.id}")
            route_ids.add(route.id)
            if route.upstream not in self.upstreams:
                raise ValueError(f"unknown upstream: {route.upstream}")
            if route.rate_limit_policy not in self.rate_policies:
                raise ValueError(f"unknown rate policy: {route.rate_limit_policy}")
        for service_id, raw_url in self.upstreams.items():
            parsed = urlsplit(raw_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"unsafe upstream URL for {service_id}")
            if parsed.username or parsed.password:
                raise ValueError(f"embedded credentials forbidden for {service_id}")
