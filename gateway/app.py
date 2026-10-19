from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .audit import AuditSink, GatewayAuditEvent, InMemoryAuditSink
from .auth import PyJWTDecoder, TokenDecoder, authenticate, authorize
from .config import GatewaySettings
from .correlation import HEADER, normalize_correlation_id
from .errors import GatewayError
from .proxy import HttpxUpstreamClient, UpstreamClient
from .rate_limit import RedisTokenBucket
from .routing import RouteRegistry


class RateLimiter(Protocol):
    async def consume(
        self, tenant_id: str, actor_id: str, route_id: str, policy: object, **kwargs: object
    ): ...


@dataclass(slots=True)
class GatewayDependencies:
    settings: GatewaySettings
    decoder: TokenDecoder
    limiter: RateLimiter
    proxy: UpstreamClient
    audit: AuditSink
    routes: RouteRegistry


def _default_dependencies(settings: GatewaySettings) -> GatewayDependencies:
    settings.validate()
    return GatewayDependencies(
        settings=settings,
        decoder=PyJWTDecoder(settings.jwt_public_key, settings.jwt_algorithm, settings.issuer),
        limiter=RedisTokenBucket.from_url(
            settings.redis_url, policy_version=settings.policy_version
        ),
        proxy=HttpxUpstreamClient(),
        audit=InMemoryAuditSink(),
        routes=RouteRegistry(settings.route_policies, settings.upstreams),
    )


def create_app(
    *,
    settings: GatewaySettings | None = None,
    dependencies: GatewayDependencies | None = None,
) -> FastAPI:
    selected = settings or GatewaySettings.from_env()
    deps = dependencies or _default_dependencies(selected)
    app = FastAPI(title="CK-NEXUS Gateway API", version="0.9.0")
    app.state.gateway = deps

    @app.exception_handler(GatewayError)
    async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", normalize_correlation_id(None))
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.public(correlation_id),
            headers={HEADER: correlation_id},
        )

    @app.middleware("http")
    async def correlation_and_size_guard(request: Request, call_next):
        correlation_id = normalize_correlation_id(request.headers.get(HEADER))
        request.state.correlation_id = correlation_id
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > deps.settings.request_size_limit_bytes:
                    raise GatewayError("REQUEST_TOO_LARGE", "Request body is too large.", 413)
            except ValueError:
                raise GatewayError("BAD_REQUEST", "Invalid Content-Length header.", 400) from None
        response = await call_next(request)
        response.headers[HEADER] = correlation_id
        return response

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "ok", "service": "ck-nexus-gateway"}

    @app.get("/health/ready")
    async def ready() -> JSONResponse:
        try:
            deps.settings.validate()
            ping = getattr(deps.limiter, "ping", None)
            if ping is not None and not await ping():
                return JSONResponse(status_code=503, content={"status": "not_ready"})
            return JSONResponse({"status": "ready", "policy_version": deps.settings.policy_version})
        except (ValueError, RuntimeError):
            return JSONResponse(status_code=503, content={"status": "not_ready"})

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"])
    async def gateway_proxy(path: str, request: Request) -> Response:
        request_path = "/" + path
        match = deps.routes.match(request_path, request.method)
        identity = authenticate(
            request.headers.get("authorization"),
            decoder=deps.decoder,
            audience=match.policy.audience,
        )
        authorize(identity, match.policy.permissions)
        rate_policy = deps.settings.rate_policies[match.policy.rate_limit_policy]
        decision = await deps.limiter.consume(
            identity.tenant_id,
            identity.actor_id,
            match.policy.id,
            rate_policy,
        )
        if not decision.allowed:
            raise GatewayError(
                "RATE_LIMITED",
                "Request limit exceeded.",
                429,
                retryable=True,
            )
        target = match.target_url(request_path)
        upstream = await deps.proxy.request(
            request.method,
            target,
            query=str(request.url.query),
            body=await request.body(),
            headers={
                **{
                    key: value
                    for key, value in request.headers.items()
                    if key.lower()
                    not in {
                        "authorization",
                        "cookie",
                        "proxy-authorization",
                        "host",
                        "content-length",
                        "connection",
                    }
                },
                HEADER: request.state.correlation_id,
                "X-CK-Tenant-ID": identity.tenant_id,
                "X-CK-Actor-ID": identity.actor_id,
                "X-CK-Permissions": ",".join(sorted(identity.permissions)),
            },
            timeout_seconds=match.policy.timeout_ms / 1000.0,
        )
        await deps.audit.emit(
            GatewayAuditEvent.create(
                correlation_id=request.state.correlation_id,
                route_id=match.policy.id,
                tenant_id=identity.tenant_id,
                actor_id=identity.actor_id,
                method=request.method,
                status_code=upstream.status_code,
                decision="proxied",
                policy_version=deps.settings.policy_version,
            )
        )
        headers = {HEADER: request.state.correlation_id}
        if upstream.headers and upstream.headers.get("location"):
            # Redirect is returned without following it.
            # Credentials are never forwarded to redirected hosts.
            headers["Location"] = upstream.headers["location"]
        return Response(
            content=upstream.body,
            status_code=upstream.status_code,
            media_type=upstream.content_type,
            headers=headers,
        )

    return app
