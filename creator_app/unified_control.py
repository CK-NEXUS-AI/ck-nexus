from __future__ import annotations

import hmac
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute

from creator_app.development_control import (
    COMPETENCY_CRITERIA,
    DevelopmentState,
    DevelopmentStatusStore,
    default_development_status_db_path,
    evaluate_competency,
)

WEB_DIR = Path(__file__).resolve().parent / "web"

CONTROL_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "id": "core",
        "title": "AI & Creator Core",
        "summary": (
            "Agents, generation runs, provider routing, creator runtime "
            "and idea generation."
        ),
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
        "summary": (
            "Skill nervous system, planning, discovery, approvals, sandbox execution "
            "and hardened pipelines."
        ),
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
        "title": "Development Council & OpenCode",
        "summary": (
            "Multi-role development council, advisory orchestration and gated "
            "OpenCode execution."
        ),
        "prefixes": ("/api/dev-team",),
        "modules": (
            "creator_app/dev_team.py",
            "orchestration/",
        ),
        "deep_link": "/demo",
    },
    {
        "id": "integrations",
        "title": "Integration & Connector Network",
        "summary": (
            "GitHub, Gmail, Slack, Drive plus dynamic MCP/OpenAPI connector "
            "discovery and activation."
        ),
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
        "summary": (
            "Email ingress, routing, attachment quarantine, deduplication, outbox "
            "and audit trail."
        ),
        "prefixes": ("/api/email",),
        "modules": ("services/email_gateway/",),
        "deep_link": "/demo",
    },
    {
        "id": "data",
        "title": "Data, Memory & Knowledge",
        "summary": (
            "Run history, sessions, persistence, migrations, durable state "
            "and idea graph data."
        ),
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
        "summary": (
            "Credential broker/vault, council authority, policy, risk, sandbox "
            "controls and evidence boundaries."
        ),
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
        "summary": (
            "Health, readiness, metrics, observability, release gates, backup/restore "
            "and billing services."
        ),
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
    development_store = DevelopmentStatusStore(
        os.environ.get(
            "CKNEXUS_DEVELOPMENT_STATUS_DB",
            str(default_development_status_db_path()),
        )
    )
    human_approval_token = os.environ.get("CKNEXUS_HUMAN_APPROVAL_TOKEN", "").strip()

    def require_human_approval_token(supplied: str | None) -> None:
        if not human_approval_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "HUMAN_APPROVAL_GATE_NOT_CONFIGURED",
                    "message": (
                        "Human approval authority is fail-closed until a separate "
                        "approval token is configured."
                    ),
                },
            )
        if not supplied or not hmac.compare_digest(supplied, human_approval_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "HUMAN_APPROVAL_REQUIRED"},
            )

    def authorize_development_mutation(
        payload: dict[str, Any],
        supplied_human_approval: str | None,
    ) -> None:
        actor_type = str(payload.get("actor_type", "")).strip().lower()
        if actor_type == "ai":
            competency_agent_id = str(
                payload.get("competency_agent_id", "")
            ).strip()
            if not competency_agent_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "COMPETENCY_AGENT_ID_REQUIRED"},
                )
            try:
                development_store.require_write_authority(competency_agent_id)
            except (KeyError, PermissionError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "AI_COMPETENCY_WRITE_GATE_BLOCKED",
                        "message": str(exc),
                    },
                ) from exc
            return

        if actor_type == "human":
            require_human_approval_token(supplied_human_approval)
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "DEVELOPMENT_ACTOR_TYPE_REQUIRED",
                "allowed": ["ai", "human"],
            },
        )

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

    @app.get(
        "/api/control/development/live",
        dependencies=[Depends(require_control_token)],
    )
    async def development_live_status() -> dict[str, Any]:
        return development_store.snapshot()

    @app.get(
        "/api/control/development/history",
        dependencies=[Depends(require_control_token)],
    )
    async def development_history(limit: int = 100) -> dict[str, Any]:
        return {"events": development_store.history(limit=limit)}

    @app.get(
        "/api/control/development/competency/criteria",
        dependencies=[Depends(require_control_token)],
    )
    async def development_competency_criteria() -> dict[str, Any]:
        return {
            "criteria": {
                level: list(items)
                for level, items in COMPETENCY_CRITERIA.items()
            },
            "pro_level_rule": {
                "minimum_score": 85,
                "level_1_all_required": True,
                "level_2_all_required": True,
                "level_3_all_required": True,
                "level_4_minimum_ratio": 0.80,
                "human_confirmation_required_for_write": True,
                "separate_human_approval_token_required": True,
                "human_approval_gate_configured": bool(human_approval_token),
            },
            "authority_denials": [
                "merge_main",
                "deploy_production",
                "change_q10_q11_q12",
                "self_approve",
            ],
        }

    @app.post(
        "/api/control/development/tasks",
        dependencies=[Depends(require_control_token)],
    )
    async def create_development_task(
        payload: dict[str, Any],
        x_cknexus_human_approval: str | None = Header(default=None),
    ) -> dict[str, Any]:
        required = ("task_id", "title", "owner", "actor")
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "MISSING_FIELDS", "fields": missing},
            )
        authorize_development_mutation(payload, x_cknexus_human_approval)
        try:
            return development_store.create_task(
                task_id=str(payload["task_id"]),
                title=str(payload["title"]),
                owner=str(payload["owner"]),
                priority=str(payload.get("priority", "P2")),
                actor=str(payload["actor"]),
                current_step=(
                    str(payload["current_step"])
                    if payload.get("current_step") is not None
                    else None
                ),
            )
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": type(exc).__name__, "message": str(exc)},
            ) from exc

    @app.post(
        "/api/control/development/tasks/{task_id}/transition",
        dependencies=[Depends(require_control_token)],
    )
    async def transition_development_task(
        task_id: str,
        payload: dict[str, Any],
        x_cknexus_human_approval: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not str(payload.get("actor", "")).strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "ACTOR_REQUIRED"},
            )
        authorize_development_mutation(payload, x_cknexus_human_approval)
        for field_name in ("human_reviewed", "merged"):
            if field_name in payload and not isinstance(payload[field_name], bool):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "BOOLEAN_FIELD_REQUIRED",
                        "field": field_name,
                    },
                )
        try:
            target_state = DevelopmentState(str(payload.get("to_state", "")))
            if target_state is DevelopmentState.COMPLETED:
                if str(payload.get("actor_type", "")).strip().lower() != "human":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={"error": "HUMAN_COMPLETION_REQUIRED"},
                    )
                require_human_approval_token(x_cknexus_human_approval)
            return development_store.transition_task(
                task_id=task_id,
                to_state=target_state,
                actor=str(payload["actor"]),
                progress=payload.get("progress"),
                current_step=payload.get("current_step"),
                eta=payload.get("eta"),
                blocker=payload.get("blocker"),
                commit_hash=payload.get("commit_hash"),
                human_reviewed=payload.get("human_reviewed", False),
                merged=payload.get("merged", False),
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "TASK_NOT_FOUND", "task_id": task_id},
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "COMPLETION_GATE_BLOCKED", "message": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "INVALID_TRANSITION", "message": str(exc)},
            ) from exc

    @app.post(
        "/api/control/development/competency/evaluate",
        dependencies=[Depends(require_control_token)],
    )
    async def evaluate_development_ai(
        payload: dict[str, Any],
        x_cknexus_human_approval: str | None = Header(default=None),
    ) -> dict[str, Any]:
        answers = payload.get("answers")
        if not isinstance(answers, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "ANSWERS_REQUIRED"},
            )
        invalid_boolean_fields = [
            str(key)
            for key, value in answers.items()
            if not isinstance(value, bool)
        ]
        if invalid_boolean_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "BOOLEAN_ANSWERS_REQUIRED",
                    "fields": invalid_boolean_fields,
                },
            )
        human_confirmed_value = payload.get("human_confirmed", False)
        if not isinstance(human_confirmed_value, bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "HUMAN_CONFIRMED_MUST_BE_BOOLEAN"},
            )
        human_confirmed = human_confirmed_value
        reviewer_type = str(payload.get("reviewer_type", "")).strip().lower()
        if human_confirmed:
            if reviewer_type != "human":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "HUMAN_CONFIRMATION_REQUIRED",
                        "message": (
                            "AI or automated evaluators cannot grant write authority."
                        ),
                    },
                )
            require_human_approval_token(x_cknexus_human_approval)
        try:
            assessment = evaluate_competency(
                agent_id=str(payload.get("agent_id", "")),
                display_name=str(payload.get("display_name", "")),
                answers={str(key): value for key, value in answers.items()},
                human_confirmed=human_confirmed,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "INVALID_ASSESSMENT", "message": str(exc)},
            ) from exc
        return development_store.save_competency(
            assessment,
            actor=str(payload.get("actor") or reviewer_type or "unknown"),
        )

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
