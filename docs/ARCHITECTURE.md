# Architecture

## Canonical application runtime

The canonical CK-NEXUS application entry point is `creator_app.unified`:

```bash
python -m creator_app.unified
```

This module constructs the base FastAPI application using `creator_app.api.create_app()` and installs the unified-control integration before starting Uvicorn. The default bind is `127.0.0.1:8000`; `CKNEXUS_HOST` and `PORT` configure the bind address and port. The corresponding Docker image also starts `python -m creator_app.unified`.

### Compatibility entry points

`main.py` (`python main.py`, and the installed `ck-nexus` project script) remains available for compatibility. It creates the base app without the unified-control installation hook. Existing `start.sh` and `start.ps1` also invoke `main.py`; `start_unified.sh` invokes the canonical unified module. They are retained to avoid breaking existing users. New onboarding and deployment instructions should use the canonical module. Do not treat compatibility entry points as equivalent to the unified runtime without checking the required integration behavior.

The `gateway/` package and its separate container are a distinct API gateway service, not an alternative launcher for the Creator application. Other demos, connectors and service-specific commands are auxiliary components, not replacements for the canonical app runtime.

## Runtime flow

```text
Browser
  │ same-origin HTTP + optional Bearer token
  ▼
FastAPI (creator_app/api.py, installed by creator_app.unified)
  ├── validation / request-size limit / rate limit / security headers
  ├── CreatorService and provider router
  │     ├── Demo Runtime, or
  │     └── OpenAI Agents SDK / configured provider
  ├── Development Council (advisory only)
  ├── AGNES bounded execution paths (gated by configuration/approvals)
  └── SQLite by default; optional configured PostgreSQL services
```

## API and health references

`creator_app/api.py` is the canonical API implementation. It defines `/health`, `/health/live`, `/health/ready`, `/api/status`, application run and agent routes, integrations, and the development dashboard routes. `/health` checks the application database; `/health/live` is process liveness; `/health/ready` reports readiness dependencies. A green CI workflow is not live application health evidence, and none of these local endpoint definitions proves production health unless actually queried in the target environment.

The OpenAPI reference is served at `/docs` when the application is running. Use the actual OpenAPI schema and route definitions as the API source of truth; older service-specific API docs may refer to a separate gateway or historical deployment.

## Configuration and secret handling

`creator_app/config.py` owns Creator application settings. It loads `.env.local` from `CKNEXUS_HOME` (or the current working directory). `.env.example` documents the variables and safe local defaults. Keep credentials in protected runtime environment or an approved secret store; never commit them or place them in dashboard snapshots. Production startup enforces required authentication and enabled integration-secret checks. Treat `.env.p0.example`, `.env.prod.example`, `.env.universal.example`, and deployment-specific Compose files as profiles for their documented deployment use, not interchangeable Creator configuration contracts.

## Storage and provider boundary

The default application store is local SQLite under `data/`; PostgreSQL/session database URLs are optional configuration paths. The browser does not receive provider API keys. Provider credentials and integrations are resolved server-side. The Development Council is advisory, and system mutations require their separate authorized and gated execution paths.

## Security and governance boundary

CK-NEXUS Core / L3 Authority remains the sole authority for state, memory, permissions, policy, execution, and evidence. External tools have `authority_level=NONE`. n8n, where used, is a workflow execution plane and is not a Q10 judge. AI agents may propose changes but cannot self-approve governance or release decisions. Independent reviewer fields stay blank until an actual independent review occurs.

Evidence follows `DESIGNED → IMPLEMENTED → EXECUTED → VERIFIED → PRODUCTION`. No evidence means no completion. Q10–Q16 production gates and their exact-subject requirements are defined in `docs/Q10_Q16_CLOSURE_CONTRACT.md` and `RELEASE_STATUS.md`; do not infer production status from CI alone.

## Deployment boundary

For local development, bind to loopback and use the documented Python quick start. For remote deployment, follow the applicable deployment guide, configure a strong `CKNEXUS_ACCESS_TOKEN`, use a maintained HTTPS reverse proxy, restrict network exposure, and protect persistent data. Use one application worker unless shared persistence and distributed rate limiting have been validated for the target configuration. Docker startup is defined by the root `Dockerfile`; compose profiles have deployment-specific dependencies and must not be mixed with the simple local quick start.

## Deferred / separate components

- `gateway/`: separately deployable API gateway.
- `integrations/`: auxiliary control bridges.
- Compose/systemd profiles: environment-specific deployment paths; not local developer startup instructions.
- PostgreSQL/Redis runtime proofs, disaster-recovery rehearsals, live-provider checks, and clean-machine verification: staging/release evidence tasks, not proven by code presence.
