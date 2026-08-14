from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute

WEB_DIR = Path(__file__).resolve().parent / "web"

CONTROL_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "id": "core",
        "title": "AI & Creator Core",
        "summary": "Agents, generation runs, provider routing, creator runtime and idea generation.",
        "prefixes": ("/api/status", "/api/agents", "/api/runs", "/api/providers"),
        "modules": (
            "creator_app/runtime.py",
            "creator_app/provider_router.py",
            "creator_app/providers.py",
            "creator_app/catalog.py",
            "idea_engine/",
        ),
        "deep_link": "/demo",
    },
    {
        "id": "skills",
        "title": "AGNES Skills & Automation",
        "summary": "Skill nervous system, planning, discovery, approvals, sandbox execution and hardened pipelines.",
        "prefixes": ("/api/agnes",),
        "modules": (
            "creator_app/skills/agnes/SKILL.md",
            "creator_app/agnes/",
            "creator_app/agnes_runtime.py",
            "creator_app/agnes_skills.py",
        ),
        "deep_link": "/docs",
    },
    {
        "id": "development",
        "title": "Development Council & Codex",
        "summary": "Multi-role development council, advisory orchestration and gated Codex execution.",
        "prefixes": ("/api/dev-team", "/api/codex"),
        "modules": (
            "creator_app/dev_team.py",
            "creator_app/codex_bridge.py",
            "orchestration/",
        ),
        "deep_link": "/demo",
    },
    {
        "id": "integrations",
        "title": "Integration & Connector Network",
        "summary": "GitHub, Gmail, Slack, Drive plus dynamic MCP/OpenAPI connector discovery and activation.",
        "prefixes": ("/api/integrations", "/api/connectors"),
        "modules": (
            "creator_app/connector_fabric/",
            "creator_app/github_app.py",
            "creator_app/github_integration.py",
            "creator_app/gmail_oauth.py",
            "creator_app/integrations.py",
        ),
        "deep_link": "/demo",
    },
    {
        "id": "communication",
        "title": "Email & Communication",
        "summary": "Email ingress, routing, attachment quarantine, deduplication, outbox and audit trail.",
        "prefixes": ("/api/email",),
        "modules": ("services/email_gateway/",),
        "deep_link": "/demo",
    },
    {
        "id": "data",
        "title": "Data, Memory & Knowledge",
        "summary": "Run history, sessions, persistence, migrations, durable state and idea graph data.",
        "prefixes": ("/api/sessions",),
        "modules": (
            "creator_app/storage.py",
            "migrations/",
            "services/email_gateway/repository.py",
            "services/email_gateway/postgres_repository.py",
            "idea_engine/graph.py",
        ),
        "deep_link": "/demo",
    },
    {
        "id": "governance",
        "title": "Governance & Security",
        "summary": "Credential broker/vault, council authority, policy, risk, sandbox controls and evidence boundaries.",
        "prefixes": ("/api/security",),
        "modules": (
            "creator_app/credential_broker.py",
            "creator_app/credential_vault.py",
            "creator_app/council_authority/",
            "creator_app/connector_fabric/governance.py",
            "creator_app/connector_fabric/security.py",
            "creator_app/agnes/execution/kill_switch.py",
        ),
        "deep_link": "/docs",
    },
    {
        "id": "operations",
        "title": "Operations & Commerce",
        "summary": "Health, readiness, metrics, observability, release gates, backup/restore and billing services.",
        "prefixes": ("/health", "/metrics"),
        "modules": (
            "observability/",
            "scripts/",
            "services/billing/",
            "deploy/",
            "docker-compose.prod.yml",
        ),
        "deep_link": "/docs",
    },
)


def _route_group(path: str) -> str:
    for group in CONTROL_GROUPS:
        if any(path.startswith(prefix) for prefix in group["prefixes"]):
            return str(group["id"])
    return "operations"


def _route_index(app: FastAPI) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith("/api/control") or route.path == "/control":
            continue
        methods = sorted(
            method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"}
        )
        routes.append(
            {
                "path": route.path,
                "methods": methods,
                "name": route.name,
                "group": _route_group(route.path),
                "protected": route.path.startswith("/api/") or route.path == "/metrics",
                "interactive_docs": "/docs" if route.include_in_schema else None,
            }
        )
    routes.sort(key=lambda item: (item["group"], item["path"], item["methods"]))
    return routes


def _safe_call(func: Any, fallback: Any = None) -> Any:
    try:
        return func()
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__} if fallback is None else fallback


def install_unified_control(app: FastAPI) -> FastAPI:
    """Attach a compact control plane without duplicating or bypassing CK-NEXUS runtime policy."""
    settings = app.state.settings

    async def require_control_token(
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = settings.access_token
        if not expected:
            return
        supplied = ""
        if authorization and authorization.startswith("Bearer "):
            supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "A valid CK-NEXUS access token is required.",
                },
            )

    @app.get("/control", include_in_schema=False)
    async def unified_control_page() -> FileResponse:
        return FileResponse(WEB_DIR / "control.html")

    @app.get("/api/control/manifest", dependencies=[Depends(require_control_token)])
    async def control_manifest() -> dict[str, Any]:
        discovered_routes = _route_index(app)
        groups: list[dict[str, Any]] = []
        for raw_group in CONTROL_GROUPS:
            group = dict(raw_group)
            group.pop("prefixes", None)
            group["routes"] = [
                route for route in discovered_routes if route["group"] == raw_group["id"]
            ]
            group["route_count"] = len(group["routes"])
            groups.append(group)
        return {
            "name": "CK-NEXUS Unified Control Surface",
            "version": settings.app_version,
            "groups": groups,
            "route_count": len(discovered_routes),
            "design": {
                "top_level_navigation": "main-groups-only",
                "subfunctions": "progressive-disclosure",
                "source_of_truth": "FastAPI route discovery + module inventory",
            },
        }

    @app.get("/api/control/status", dependencies=[Depends(require_control_token)])
    async def control_status() -> dict[str, Any]:
        store = app.state.store
        provider_router = app.state.provider_router
        preferred = _safe_call(
            lambda: provider_router.preferred_status(required_capabilities={"text"})
        )
        providers = _safe_call(lambda: provider_router.statuses(), ())
        connector_fabric = app.state.connector_fabric
        connectors = (
            _safe_call(lambda: connector_fabric.registry.list(), ())
            if connector_fabric is not None
            else ()
        )
        github = _safe_call(lambda: app.state.github_integration.status().as_dict())
        slack = _safe_call(lambda: app.state.slack_integration.status().as_dict())
        drive = _safe_call(lambda: app.state.drive_integration.status().as_dict())
        gmail = _safe_call(lambda: app.state.gmail_oauth.status())
        vault = app.state.credential_vault
        return {
            "version": settings.app_version,
            "environment": settings.environment,
            "database": {"ready": bool(_safe_call(store.ping, False))},
            "ai": {
                "ready": bool(getattr(app.state.service.runtime, "ready", False)),
                "preferred": getattr(preferred, "name", None),
                "providers": len(providers),
            },
            "skills": {
                "agnes_enabled": bool(settings.agnes_enabled),
                "skill_count": len(_safe_call(app.state.agnes.skills, ())),
                "phase3_enabled": bool(settings.agnes_phase3_enabled),
            },
            "development": {
                "council_enabled": bool(settings.dev_team_enabled),
                "council_ready": bool(app.state.dev_team.ready),
                "codex_enabled": bool(settings.codex_enabled),
                "codex_ready": bool(app.state.codex_bridge.ready),
            },
            "integrations": {
                "github": github,
                "gmail": gmail,
                "slack": slack,
                "google_drive": drive,
                "dynamic_connector_fabric": connector_fabric is not None,
                "dynamic_connector_count": len(connectors),
            },
            "security": {
                "credential_vault_enabled": vault is not None,
                "access_token_required": bool(settings.access_token),
                "secrets_exposed": False,
            },
            "email": {"enabled": bool(settings.email_gateway_enabled)},
            "operations": {
                "runtime_binding_required": bool(app.state.runtime_binding_required),
                "metrics_enabled": True,
            },
        }

    return app
