from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import Path as FilePath

from fastapi import Depends, FastAPI, File, Header, HTTPException, Path, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from creator_app.agnes_runtime import AgnesNervousSystem, AgnesPolicy
from creator_app.catalog import get_agent_spec, list_agent_cards
from creator_app.codex_bridge import (
    CodexBridge,
    CodexBridgeRuntimeError,
    CodexBridgeUnavailableError,
)
from creator_app.config import Settings
from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.credential_vault import build_credential_vault
from creator_app.gmail_oauth import GmailOAuthError, GmailOAuthManager
from creator_app.github_app import GitHubAppAuth, GitHubAppAuthError
from creator_app.providers import build_provider_router
from creator_app.dev_team import DevTeamRuntime
from creator_app.github_integration import GitHubIntegration
from creator_app.health import DependencyState, DependencyStatus, evaluate_health
from creator_app.integrations import GoogleDriveIntegration, SlackIntegration
from creator_app.rate_limit import SlidingWindowRateLimiter
from creator_app.runtime import CreatorRuntime, MissingCredentialError, ProviderRuntimeError
from creator_app.schemas import (
    AgnesApprovalRequest,
    AgnesExecuteRequest,
    AgnesPipelineStartRequest,
    AgnesPipelineDiscardRequest,
    CodexTaskRequest,
    CodexTaskResult,
    DevTeamRequest,
    DevTeamResult,
    RunRequest,
    RunResult,
    StatusResponse,
)
from creator_app.service import CreatorService
from creator_app.storage import RunStore
from services.email_gateway.factory import create_email_repository
from services.email_gateway.schemas import (
    EmailIngressRequest,
    EmailIngressResult,
    LeaseRecoveryResult,
    LoopCheckRequest,
    LoopCheckResult,
    OutboxClaimItem,
    OutboxClaimRequest,
    OutboxClaimResult,
    OutboxRequest,
    OutboxResult,
    OutboxRetryRequest,
    OutboxSentRequest,
    RoutingRequest,
    RoutingResult,
)
from services.email_gateway.attachments import scan_attachment
from services.email_gateway.loop_prevention import evaluate_loop_headers
from services.email_gateway.routing import route_email

WEB_DIR = FilePath(__file__).resolve().parent / "web"
SESSION_ID_PATTERN = r"^[A-Za-z0-9_:-]+$"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_settings.validate_startup()
    credential_vault = build_credential_vault(
        enabled=resolved_settings.credential_vault_enabled,
        path=resolved_settings.credential_vault_path,
    )
    credential_broker = CredentialBroker.from_environment(
        persistent_store=credential_vault
    )
    provider_router = build_provider_router(resolved_settings, credential_broker)
    store = RunStore(resolved_settings.database_path, database_url=resolved_settings.database_url)
    runtime = CreatorRuntime(
        resolved_settings,
        provider_router=provider_router,
        credential_broker=credential_broker,
    )
    codex_bridge = CodexBridge(resolved_settings)
    service = CreatorService(resolved_settings, runtime, store)
    dev_team = DevTeamRuntime(
        resolved_settings,
        provider_router=provider_router,
        credential_broker=credential_broker,
    )
    agnes_skill_file = FilePath(__file__).resolve().parent / "skills" / "agnes" / "SKILL.md"
    agnes = AgnesNervousSystem(
        skill_file=agnes_skill_file,
        ledger_path=resolved_settings.agnes_ledger_path,
        provider_router=provider_router,
        policy=AgnesPolicy(max_parallel_skills=resolved_settings.agnes_max_parallel_skills),
        credential_broker=credential_broker,
        sandbox_enabled=resolved_settings.agnes_sandbox_enabled,
        sandbox_root=resolved_settings.agnes_sandbox_root,
        sandbox_repository_root=resolved_settings.agnes_sandbox_repository_root,
        phase3_enabled=resolved_settings.agnes_phase3_enabled,
        environment=resolved_settings.environment,
        phase3_redis_url=resolved_settings.agnes_redis_url,
        phase3_cgroup_root=resolved_settings.agnes_cgroup_root,
    )
    gmail_oauth = GmailOAuthManager(
        credential_broker,
        enabled=resolved_settings.gmail_oauth_enabled,
        redirect_uri=resolved_settings.gmail_redirect_uri,
        include_send_scope=resolved_settings.gmail_send_enabled,
        timeout_seconds=resolved_settings.integration_timeout_seconds,
    )
    github_app_auth = GitHubAppAuth(
        credential_broker,
        enabled=resolved_settings.github_app_enabled,
        timeout_seconds=resolved_settings.integration_timeout_seconds,
        api_version=resolved_settings.github_api_version,
    )
    github_integration = GitHubIntegration(
        resolved_settings.github_token,
        repository=resolved_settings.github_repo,
        api_base=resolved_settings.github_api_base,
    )
    slack_integration = SlackIntegration(
        resolved_settings.slack_bot_token,
        api_base=resolved_settings.slack_api_base,
        timeout=resolved_settings.integration_timeout_seconds,
    )
    drive_integration = GoogleDriveIntegration(
        resolved_settings.google_drive_access_token,
        api_base=resolved_settings.google_drive_api_base,
        timeout=resolved_settings.integration_timeout_seconds,
    )
    email_database_path = resolved_settings.email_database_path or resolved_settings.database_path
    email_repository = create_email_repository(
        database_url=resolved_settings.email_database_url,
        database_path=email_database_path,
    )
    limiter = SlidingWindowRateLimiter(resolved_settings.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.initialize()
        if resolved_settings.email_gateway_enabled:
            email_repository.initialize()
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Menu-driven creator agents with local history.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.credential_vault = credential_vault
    app.state.credential_broker = credential_broker
    app.state.provider_router = provider_router
    app.state.store = store
    app.state.service = service
    app.state.dev_team = dev_team
    app.state.agnes = agnes
    app.state.gmail_oauth = gmail_oauth
    app.state.github_app_auth = github_app_auth
    app.state.github_integration = github_integration
    app.state.slack_integration = slack_integration
    app.state.drive_integration = drive_integration
    app.state.codex_bridge = codex_bridge
    app.state.email_repository = email_repository

    async def require_access_token(
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = resolved_settings.access_token
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

    async def require_codex_access_token(
        authorization: str | None = Header(default=None),
    ) -> None:
        if not resolved_settings.codex_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "CODEX_DISABLED", "message": "Codex Bridge is disabled."},
            )
        if not resolved_settings.access_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "CODEX_ACCESS_TOKEN_REQUIRED",
                    "message": "Set CKNEXUS_ACCESS_TOKEN before enabling Codex Bridge.",
                },
            )
        await require_access_token(authorization)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if request.method in {"POST", "PUT", "PATCH"} and content_length:
            try:
                too_large = int(content_length) > resolved_settings.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={
                        "error": "REQUEST_TOO_LARGE",
                        "message": "The request body exceeds the configured limit.",
                    },
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        return response

    @app.exception_handler(MissingCredentialError)
    async def missing_credential_handler(_: Request, exc: MissingCredentialError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "OPENAI_API_KEY_MISSING", "message": str(exc)},
        )

    @app.exception_handler(KeyError)
    async def unknown_agent_handler(_: Request, exc: KeyError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "AGENT_NOT_FOUND", "message": str(exc)},
        )

    @app.exception_handler(ProviderRuntimeError)
    async def provider_error_handler(_: Request, exc: ProviderRuntimeError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "AI_PROVIDER_ERROR", "message": str(exc)},
        )

    @app.exception_handler(GmailOAuthError)
    async def gmail_oauth_error_handler(_: Request, exc: GmailOAuthError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "GMAIL_OAUTH_ERROR", "message": str(exc)},
        )

    @app.exception_handler(GitHubAppAuthError)
    async def github_app_error_handler(_: Request, exc: GitHubAppAuthError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "GITHUB_APP_AUTH_ERROR", "message": str(exc)},
        )

    @app.exception_handler(CodexBridgeUnavailableError)
    async def codex_unavailable_handler(_: Request, exc: CodexBridgeUnavailableError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "CODEX_UNAVAILABLE", "message": str(exc)},
        )

    @app.exception_handler(CodexBridgeRuntimeError)
    async def codex_runtime_handler(_: Request, exc: CodexBridgeRuntimeError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": "CODEX_RUNTIME_ERROR", "message": str(exc)},
        )

    async def require_email_webhook_token(
        x_ck_nexus_webhook_token: str | None = Header(default=None),
    ) -> None:
        if not resolved_settings.email_gateway_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "EMAIL_GATEWAY_DISABLED",
                    "message": "Email Gateway is disabled.",
                },
            )
        expected = resolved_settings.email_webhook_token
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "EMAIL_WEBHOOK_TOKEN_REQUIRED",
                    "message": "Set CKNEXUS_EMAIL_WEBHOOK_TOKEN before enabling Email Gateway.",
                },
            )
        supplied = (x_ck_nexus_webhook_token or "").strip()
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED_EMAIL_WEBHOOK",
                    "message": "A valid CK-NEXUS webhook token is required.",
                },
            )

    async def enforce_run_rate_limit(request: Request) -> None:
        client_key = request.client.host if request.client else "unknown"
        retry_after = limiter.check(client_key)
        if retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "RATE_LIMITED",
                    "message": "Too many generation requests. Please wait and retry.",
                },
                headers={"Retry-After": str(retry_after)},
            )

    @app.post("/api/email/ingest", response_model=EmailIngressResult)
    async def email_ingest(
        payload: EmailIngressRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> EmailIngressResult:
        claim = email_repository.claim_message(
            mailbox=payload.mailbox,
            provider=payload.provider,
            provider_message_id=payload.provider_message_id,
            internet_message_id=payload.internet_message_id,
            claimed_by=payload.execution_id,
            lease_seconds=resolved_settings.email_lease_seconds,
        )
        email_repository.audit(
            email_journal_id=claim.journal_id,
            event_type="INGRESS_ACCEPTED" if claim.claimed else "INGRESS_DUPLICATE",
            actor_type="cknexus-email-worker",
            actor_id=payload.execution_id,
            action="atomic_claim",
            result="PASS",
            details={
                "mailbox": payload.mailbox,
                "provider": payload.provider,
                "duplicate_reason": claim.duplicate_reason,
            },
        )
        return EmailIngressResult(
            status="accepted" if claim.claimed else "duplicate",
            journal_id=claim.journal_id,
            duplicate_reason=claim.duplicate_reason,
        )

    @app.post("/api/email/outbox", response_model=OutboxResult)
    async def email_outbox(
        payload: OutboxRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> OutboxResult:
        created, outbox_id = email_repository.enqueue_outbox(
            email_journal_id=payload.journal_id,
            action_type=payload.action_type,
            destination=payload.destination,
            payload=payload.payload,
            deduplication_key=payload.deduplication_key,
        )
        email_repository.audit(
            email_journal_id=payload.journal_id,
            event_type="OUTBOX_ENQUEUED" if created else "OUTBOX_DUPLICATE",
            actor_type="cknexus-email-worker",
            action=payload.action_type,
            result="PASS",
            details={"outbox_id": outbox_id, "destination": payload.destination},
        )
        return OutboxResult(created=created, outbox_id=outbox_id)

    @app.post("/api/email/route", response_model=RoutingResult)
    async def email_route(
        payload: RoutingRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> RoutingResult:
        decision = route_email(
            matched_alias=payload.matched_alias,
            subject=payload.subject,
            sender=payload.sender,
            quarantined=payload.quarantined,
        )
        return RoutingResult(
            category=decision.category,
            priority=decision.priority,
            matched_rule=decision.matched_rule,
            reasons=list(decision.reasons),
        )

    @app.post("/api/email/loop-check", response_model=LoopCheckResult)
    async def email_loop_check(
        payload: LoopCheckRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> LoopCheckResult:
        decision = evaluate_loop_headers(
            payload.headers, system_addresses=set(payload.system_addresses)
        )
        return LoopCheckResult(
            allow_automatic_reply=decision.allow_automatic_reply, reason=decision.reason
        )

    @app.post("/api/email/scan-attachment")
    async def email_scan_attachment(
        file: UploadFile = File(...),
        _: None = Depends(require_email_webhook_token),
    ) -> dict[str, object]:
        import tempfile

        suffix = FilePath(file.filename or "attachment.bin").suffix
        total = 0
        temp_path: FilePath | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                temp_path = FilePath(handle.name)
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 25 * 1024 * 1024:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail={"error": "ATTACHMENT_TOO_LARGE"},
                        )
                    handle.write(chunk)
            result = scan_attachment(temp_path)
            return {
                "safe": result.safe,
                "status": result.status,
                "reason": result.reason,
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "extension": result.extension,
                "detected_mime": result.detected_mime,
            }
        finally:
            await file.close()
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    @app.post("/api/email/outbox/claim", response_model=OutboxClaimResult)
    async def email_outbox_claim(
        payload: OutboxClaimRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> OutboxClaimResult:
        items = email_repository.claim_outbox_batch(
            worker_id=payload.worker_id,
            limit=payload.limit,
            lease_seconds=payload.lease_seconds,
        )
        return OutboxClaimResult(
            items=[
                OutboxClaimItem(
                    id=item.id,
                    email_journal_id=item.email_journal_id,
                    action_type=item.action_type,
                    destination=item.destination,
                    payload=item.payload,
                    deduplication_key=item.deduplication_key,
                    attempt_count=item.attempt_count,
                )
                for item in items
            ]
        )

    @app.post("/api/email/outbox/{outbox_id}/sent")
    async def email_outbox_sent(
        outbox_id: str,
        payload: OutboxSentRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> dict[str, str]:
        email_repository.mark_outbox_sent(
            outbox_id, provider_message_id=payload.provider_message_id
        )
        row = email_repository.get_outbox(outbox_id) if hasattr(email_repository, "get_outbox") else None
        if row and row.get("email_journal_id"):
            email_repository.audit(
                email_journal_id=str(row["email_journal_id"]),
                event_type="OUTBOX_SENT",
                actor_type="cknexus-email-worker",
                action="send",
                result="PASS",
                details={"outbox_id": outbox_id, "provider_message_id": payload.provider_message_id},
            )
        return {"status": "sent"}

    @app.post("/api/email/outbox/{outbox_id}/retry")
    async def email_outbox_retry(
        outbox_id: str,
        payload: OutboxRetryRequest,
        _: None = Depends(require_email_webhook_token),
    ) -> dict[str, str]:
        email_repository.mark_outbox_retry(outbox_id, error=payload.error)
        return {"status": "retry_scheduled"}

    @app.post("/api/email/recover", response_model=LeaseRecoveryResult)
    async def email_recover(
        _: None = Depends(require_email_webhook_token),
    ) -> LeaseRecoveryResult:
        recovered = email_repository.recover_expired_leases()
        return LeaseRecoveryResult(**recovered)

    @app.get("/api/email/audit/{journal_id}")
    async def email_audit_trace(
        journal_id: str,
        _: None = Depends(require_email_webhook_token),
    ) -> dict[str, object]:
        return {"journal_id": journal_id, "events": email_repository.trace_audit(journal_id)}

    @app.get("/health")
    async def health():
        if not store.ping():
            return JSONResponse(status_code=503, content={"status": "degraded", "version": resolved_settings.app_version, "database": "unavailable"})
        return {"status": "ok", "version": resolved_settings.app_version, "database": "ok"}

    @app.get("/health/live")
    async def health_live() -> dict[str, object]:
        """Process liveness only; dependency outages do not turn this probe off."""
        return evaluate_health(process_live=True).as_dict()

    @app.get("/health/ready")
    async def health_ready():
        """Readiness with stable dependency cause codes for supervisors and operators."""
        database_ready = store.ping()
        ai_ready = runtime.ready
        report = evaluate_health(
            (
                DependencyStatus(
                    "database",
                    DependencyState.HEALTHY if database_ready else DependencyState.UNAVAILABLE,
                    required=True,
                ),
                DependencyStatus(
                    "ai-provider",
                    DependencyState.HEALTHY if ai_ready else DependencyState.UNAVAILABLE,
                    required=False,
                ),
            )
        )
        payload = report.as_dict()
        payload["version"] = resolved_settings.app_version
        if report.ready:
            return payload
        return JSONResponse(status_code=503, content=payload)

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics(_: None = Depends(require_access_token)) -> str:
        lines = [
            "# HELP ckn_build_info CK-NEXUS build metadata.",
            "# TYPE ckn_build_info gauge",
            f'ckn_build_info{{version="{resolved_settings.app_version}"}} 1',
        ]
        if resolved_settings.email_gateway_enabled:
            snapshot = email_repository.metrics_snapshot()
            metrics_map = {
                "journal_total": "ckn_email_journal_total",
                "duplicates_total": "ckn_email_duplicate_total",
                "outbox_pending": "ckn_email_outbox_pending",
                "outbox_sending": "ckn_email_outbox_sending",
                "stale_journal_leases": "ckn_email_stale_processing_leases",
            }
            for key, metric_name in metrics_map.items():
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name} {snapshot[key]}")
        return "\n".join(lines) + "\n"

    @app.get("/api/status", response_model=StatusResponse)
    async def app_status() -> StatusResponse:
        if resolved_settings.mock_ai:
            mode = "mock"
            model = "mock"
        else:
            preferred = provider_router.preferred_status(required_capabilities={"text"})
            mode = preferred.name if preferred is not None else "blocked"
            model = (
                resolved_settings.ollama_model
                if mode == "ollama"
                else resolved_settings.openai_model
            )
        openai_key_configured = credential_broker.is_configured(
            CredentialId.OPENAI_API_KEY, consumer="provider.openai"
        )
        return StatusResponse(
            name=resolved_settings.app_name,
            version=resolved_settings.app_version,
            mode=mode,
            model=model,
            key_configured=openai_key_configured,
            database_ready=store.ping(),
            access_required=bool(resolved_settings.access_token),
            codex_enabled=resolved_settings.codex_enabled,
            codex_ready=codex_bridge.ready,
            codex_sandbox=resolved_settings.codex_sandbox,
            dev_team_enabled=resolved_settings.dev_team_enabled,
            dev_team_ready=dev_team.ready,
        )

    @app.get("/api/integrations/github/status")
    async def github_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        return github_integration.status().as_dict()

    @app.post("/api/integrations/github/test")
    async def github_test(_: None = Depends(require_access_token)) -> dict[str, object]:
        return github_integration.status().as_dict()

    @app.get("/api/integrations/status")
    async def integrations_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        github = github_integration.status().as_dict()
        github_normalized = {
            "id": "github",
            "configured": github["configured"],
            "connected": bool(github["connected"] and github["repository_access"]),
            "message": github["message"],
            "details": {
                "login": github["login"],
                "repository": github["repository"],
                "repository_access": github["repository_access"],
                "default_branch": github["default_branch"],
            },
        }
        openai_configured = credential_broker.is_configured(
            CredentialId.OPENAI_API_KEY, consumer="provider.openai"
        )
        openai_status = {
            "id": "openai",
            "configured": openai_configured,
            "connected": False,
            "message": (
                "OpenAI credential is brokered; live connectivity remains an AI001 runtime gate."
                if openai_configured
                else "OpenAI credential is not configured in the credential broker."
            ),
            "details": {"model": resolved_settings.openai_model, "live_test_required": True},
        }
        local_status = {
            "id": "database",
            "configured": True,
            "connected": store.ping(),
            "message": "Application database is reachable." if store.ping() else "Application database is unavailable.",
            "details": {"backend": "postgresql" if resolved_settings.database_url else "sqlite"},
        }
        integrations = [
            github_normalized,
            slack_integration.status().as_dict(),
            drive_integration.status().as_dict(),
            gmail_oauth.status(),
            github_app_auth.status(),
            openai_status,
            local_status,
        ]
        return {
            "release_status": "release_candidate",
            "production_gate": "NO-GO until required P0 runtime evidence passes",
            "integrations": integrations,
        }

    @app.post("/api/integrations/test-all")
    async def integrations_test_all(_: None = Depends(require_access_token)) -> dict[str, object]:
        return await integrations_status(_)

    @app.get("/api/providers/status")
    async def providers_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        providers = []
        for item in provider_router.statuses():
            providers.append(
                {
                    "name": item.name,
                    "kind": item.kind.value,
                    "available": item.available,
                    "circuit_open": item.circuit_open,
                    "consecutive_failures": item.consecutive_failures,
                    "capabilities": sorted(item.capabilities.features),
                    "models": list(item.capabilities.models),
                }
            )
        preferred = provider_router.preferred_status(required_capabilities={"text"})
        return {
            "preferred": preferred.name if preferred is not None else None,
            "policy": {
                "local_first": provider_router.policy.local_first,
                "allow_cloud": provider_router.policy.allow_cloud,
                "max_attempts": provider_router.policy.max_attempts,
            },
            "providers": providers,
        }

    @app.get("/api/security/credentials/status")
    async def credential_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        consumers = ("provider.openai", "council.openai", "gmail.oauth", "gmail.api", "github.app")
        return {
            "secrets_exposed": False,
            "consumers": {
                consumer: [item.as_dict() for item in credential_broker.statuses(consumer=consumer)]
                for consumer in consumers
            },
        }

    @app.get("/api/security/credential-vault/status")
    async def credential_vault_status(
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return {
            "enabled": credential_vault is not None,
            "backend": "sqlite-fernet" if credential_vault is not None else None,
            "key_configured": resolved_settings.credential_vault_key_configured,
            "secrets_exposed": False,
        }

    @app.get("/api/security/credential-vault/audit")
    async def credential_vault_audit(
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        events = credential_vault.audit_events() if credential_vault is not None else ()
        return {
            "enabled": credential_vault is not None,
            "events": [event.as_dict() for event in events],
            "secrets_exposed": False,
        }

    @app.get("/api/integrations/gmail/status")
    async def gmail_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        return gmail_oauth.status()

    @app.get("/api/integrations/gmail/oauth/start")
    async def gmail_oauth_start(_: None = Depends(require_access_token)) -> dict[str, object]:
        return {"authorization_url": gmail_oauth.authorization_url()}

    @app.get("/api/integrations/gmail/oauth/callback")
    def gmail_oauth_callback(code: str = Query(...), state: str = Query(...)) -> dict[str, object]:
        return {"status": "authorized", "gmail": gmail_oauth.exchange_code(code=code, state=state)}

    @app.post("/api/integrations/gmail/revoke-local")
    async def gmail_revoke_local(
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return {"status": "revoked", "gmail": gmail_oauth.revoke_local_tokens()}

    @app.get("/api/integrations/github-app/status")
    async def github_app_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        return github_app_auth.status()

    @app.post("/api/integrations/github-app/token")
    def github_app_token(_: None = Depends(require_access_token)) -> dict[str, object]:
        return github_app_auth.ensure_installation_token()

    @app.get("/api/codex/status")
    async def codex_status(_: None = Depends(require_access_token)) -> dict[str, bool | str]:
        return {
            "enabled": resolved_settings.codex_enabled,
            "ready": codex_bridge.ready,
            "binary_available": codex_bridge.binary_available,
            "workspace_ready": codex_bridge.workspace_ready,
            "sandbox": resolved_settings.codex_sandbox,
        }

    @app.post("/api/codex/tasks", response_model=CodexTaskResult)
    async def create_codex_task(
        payload: CodexTaskRequest,
        _: None = Depends(require_codex_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> CodexTaskResult:
        result = await codex_bridge.run(payload.prompt)
        return CodexTaskResult(
            output=result.output,
            sandbox=resolved_settings.codex_sandbox,
            duration_ms=result.duration_ms,
        )


    @app.get("/api/agnes/status")
    async def agnes_status(_: None = Depends(require_access_token)) -> dict[str, object]:
        if not resolved_settings.agnes_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "AGNES_DISABLED", "message": "AGNES skill nervous system is disabled."},
            )
        return agnes.status()

    @app.get("/api/agnes/execution/status")
    async def agnes_execution_status(
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return agnes.dispatcher.status()

    @app.post("/api/agnes/execute")
    async def agnes_execute(
        payload: AgnesExecuteRequest,
        _: None = Depends(require_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> dict[str, object]:
        skill = agnes.registry.get(payload.skill_id)
        plan_step = {
            "id": skill.id,
            "version": skill.version,
            "executor": payload.executor or skill.executor,
            "inputs": payload.inputs,
            "timeout_seconds": payload.timeout_seconds,
            "allowlist_paths": payload.allowlist_paths,
            "granted_capabilities": payload.granted_capabilities,
        }
        result = await agnes.execute_skill(
            plan_step,
            goal=payload.goal,
            correlation_id=payload.correlation_id or f"agnes_api_{uuid4().hex}",
            tenant_id=payload.tenant_id,
            actor_id=payload.actor_id,
            environment=payload.environment,
            workspace_id=payload.workspace_id,
            baseline_commit=payload.baseline_commit,
            approval_id=payload.approval_id,
            idempotency_key=payload.idempotency_key,
        )
        return result.as_dict()

    @app.post("/api/agnes/pipeline/start")
    async def agnes_pipeline_start(
        payload: AgnesPipelineStartRequest,
        _: None = Depends(require_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> dict[str, object]:
        if agnes.dev_controller is None:
            raise HTTPException(status_code=503, detail={"error": "AGNES_PHASE3_DISABLED"})
        from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest
        execution_id = f"agnes_pipe_exec_{uuid4().hex}"
        workspace_id = payload.workspace_id or execution_id
        request = SkillExecutionRequest(
            execution_id=execution_id,
            correlation_id=payload.correlation_id or f"agnes_pipe_{uuid4().hex}",
            skill_id="hands.code_patch",
            skill_version=agnes.registry.get("hands.code_patch").version,
            executor=ExecutorType.SANDBOX,
            goal=payload.goal,
            inputs={"patch": payload.patch, "test_command": payload.test_command, "scan_command": payload.scan_command},
            tenant_id=payload.tenant_id, actor_id=payload.actor_id, environment=payload.environment,
            workspace_id=workspace_id, baseline_commit=payload.baseline_commit,
            approval_id=payload.approval_id, idempotency_key=payload.idempotency_key,
            allowlist_paths=tuple(payload.allowlist_paths),
            granted_capabilities=("code_write", "patch"),
        )
        handle = await agnes.dev_controller.start_pipeline(request)
        status_obj = await agnes.dev_controller.run_to_candidate(handle)
        return status_obj.as_dict()

    @app.post("/api/agnes/pipeline/{pipeline_id}/advance")
    async def agnes_pipeline_advance(
        pipeline_id: str,
        _: None = Depends(require_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> dict[str, object]:
        if agnes.dev_controller is None:
            raise HTTPException(status_code=503, detail={"error": "AGNES_PHASE3_DISABLED"})
        try:
            from creator_app.agnes.execution.phase3 import PipelineHandle
            current = await agnes.dev_controller.get_status(pipeline_id)
            status_obj = await agnes.dev_controller.run_to_candidate(
                PipelineHandle(pipeline_id, current.execution_id)
            )
            return status_obj.as_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail={"error": "PIPELINE_NOT_FOUND"})

    @app.get("/api/agnes/pipeline/{pipeline_id}")
    async def agnes_pipeline_status(
        pipeline_id: str,
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        if agnes.dev_controller is None:
            raise HTTPException(status_code=503, detail={"error": "AGNES_PHASE3_DISABLED"})
        try:
            status_obj = await agnes.dev_controller.get_status(pipeline_id)
        except KeyError:
            raise HTTPException(status_code=404, detail={"error": "PIPELINE_NOT_FOUND"})
        body = status_obj.as_dict()
        if status_obj.state.value == "candidate_ready":
            body["candidate"] = (await agnes.dev_controller.collect_candidate(pipeline_id)).as_dict()
        return body

    @app.post("/api/agnes/pipeline/{pipeline_id}/discard")
    async def agnes_pipeline_discard(
        pipeline_id: str,
        payload: AgnesPipelineDiscardRequest,
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        if agnes.dev_controller is None:
            raise HTTPException(status_code=503, detail={"error": "AGNES_PHASE3_DISABLED"})
        try:
            await agnes.dev_controller.discard(pipeline_id, payload.reason)
            return (await agnes.dev_controller.get_status(pipeline_id)).as_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail={"error": "PIPELINE_NOT_FOUND"})

    @app.post("/api/agnes/approvals")
    async def agnes_approval(
        payload: AgnesApprovalRequest,
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        grant = agnes.approvals.grant(
            approval_id=payload.approval_id,
            fingerprint=payload.fingerprint,
            approved_by=payload.approved_by,
            ttl_seconds=payload.ttl_seconds,
        )
        return {
            "approval_id": grant.approval_id,
            "approved_by": grant.approved_by,
            "expires_at": grant.expires_at,
            "fingerprint": grant.fingerprint,
        }

    @app.get("/api/agnes/skills")
    async def agnes_skills(_: None = Depends(require_access_token)) -> dict[str, object]:
        return {"agent": "AGNES", "skills": agnes.skills()}

    @app.get("/api/agnes/plan")
    async def agnes_plan(
        goal: str = Query(min_length=1, max_length=4000),
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return agnes.plan(goal)

    @app.get("/api/agnes/discovery-sources")
    async def agnes_discovery_sources(
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return {"sources": agnes.discovery_sources()}

    @app.get("/api/agnes/model-watch-plan")
    async def agnes_model_watch_plan(
        limit: int = Query(default=50, ge=1, le=50),
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return agnes.model_watch_plan(limit=limit)

    @app.get("/api/agnes/upgrade-plan")
    async def agnes_upgrade_plan(
        goal: str = Query(min_length=1, max_length=4000),
        _: None = Depends(require_access_token),
    ) -> dict[str, object]:
        return agnes.self_upgrade_plan(goal)

    @app.get("/api/dev-team")
    async def dev_team_roster(_: None = Depends(require_access_token)) -> dict[str, object]:
        return {
            "enabled": resolved_settings.dev_team_enabled,
            "ready": dev_team.ready,
            "mode": (
                "mock"
                if resolved_settings.mock_ai
                else (
                    provider_router.preferred_status(
                        required_capabilities={"agents-sdk"}
                    ).name
                    if provider_router.preferred_status(
                        required_capabilities={"agents-sdk"}
                    ) is not None
                    else "blocked"
                )
            ),
            "orchestrator": "CK-NEXUS Lead Orchestrator",
            "web_search_enabled": resolved_settings.dev_team_web_search_enabled,
            "advisors": dev_team.roster(),
            "side_effect_policy": "advisory-only; execution requires a separate gated path",
        }

    @app.post("/api/dev-team/run", response_model=DevTeamResult)
    async def run_dev_team(
        payload: DevTeamRequest,
        _: None = Depends(require_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> DevTeamResult:
        if len(payload.prompt) > resolved_settings.max_prompt_chars:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "PROMPT_TOO_LONG", "message": "Development brief is too long."},
            )
        if not resolved_settings.dev_team_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "DEV_TEAM_DISABLED", "message": "Development Council is disabled."},
            )
        return await dev_team.run(payload)

    @app.get("/api/agents")
    async def agents(_: None = Depends(require_access_token)):
        return {"agents": list_agent_cards()}

    @app.post("/api/runs", response_model=RunResult)
    async def create_run(
        payload: RunRequest,
        _: None = Depends(require_access_token),
        __: None = Depends(enforce_run_rate_limit),
    ) -> RunResult:
        if len(payload.prompt) > resolved_settings.max_prompt_chars:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "PROMPT_TOO_LONG", "message": "Creative brief is too long."},
            )
        get_agent_spec(payload.agent_id)
        return await service.create_run(payload)

    @app.get("/api/runs", response_model=list[RunResult])
    async def list_runs(
        session_id: str | None = Query(
            default=None,
            min_length=1,
            max_length=96,
            pattern=SESSION_ID_PATTERN,
        ),
        limit: int = Query(default=20, ge=1, le=100),
        _: None = Depends(require_access_token),
    ) -> list[RunResult]:
        return store.list(limit=min(limit, resolved_settings.history_limit), session_id=session_id)

    @app.get("/api/runs/{run_id}", response_model=RunResult)
    async def get_run(
        run_id: str,
        _: None = Depends(require_access_token),
    ) -> RunResult:
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.delete("/api/sessions/{session_id}")
    async def delete_session(
        session_id: str = Path(
            min_length=1,
            max_length=96,
            pattern=SESSION_ID_PATTERN,
        ),
        _: None = Depends(require_access_token),
    ) -> dict[str, int | str]:
        deleted = store.delete_session(session_id)
        try:
            if resolved_settings.session_database_url:
                from agents.extensions.memory import SQLAlchemySession
                agent_session = SQLAlchemySession.from_url(
                    session_id,
                    url=resolved_settings.session_database_url,
                    create_tables=True,
                    ensure_ascii=False,
                )
                await agent_session.clear_session()
                await agent_session.engine.dispose()
            else:
                from agents import SQLiteSession
                agent_session = SQLiteSession(session_id, db_path=resolved_settings.database_path)
                await agent_session.clear_session()
                agent_session.close()
        except ImportError:
            # Local/mock tests may intentionally run without the optional Agents SDK installed.
            # Creator history deletion must still succeed; production images install the SDK.
            pass
        return {"status": "deleted", "records": deleted}

    @app.get("/demo", include_in_schema=False)
    async def full_system_demo() -> FileResponse:
        return FileResponse(WEB_DIR / "full-system.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    return app
