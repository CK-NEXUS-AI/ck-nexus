# CK-NEXUS Installation Guide — Canonical Runtime

## Runtime and deployment authority

CK-NEXUS has one application composition root: `creator_app.unified`.
It composes `creator_app.api.create_app()` with the unified control plane. Every supported
launcher, package command, Docker image, and systemd service must invoke this same runtime.
`main.py` remains a compatibility entry point and delegates to the canonical runtime; it must
not construct a second FastAPI application.

Deployment definitions have distinct purposes but share the same image and runtime:

- `docker-compose.p0.yml` — isolated P0/staging validation.
- `docker-compose.prod.yml` — production deployment.

Do not treat these as separate application implementations. Production deployment and release
evidence must use the production compose definition and the exact release subject under review.

## 1. Requirements

- 64-bit Linux host with Docker Engine and Docker Compose plugin
- Persistent storage for PostgreSQL, Redis, and backups
- TLS reverse proxy for internet-facing endpoints
- Customer-controlled provider credentials for Live Mode
- Customer-controlled email/OAuth credentials when those integrations are enabled

## 2. Configuration and secrets

Keep the runtime environment file outside the repository and restrict it to the service owner
(`chmod 600`). Never commit API keys, OAuth tokens, database passwords, or bearer tokens.

The production compose file requires:

- `CKNEXUS_DB_PASSWORD`
- `CKNEXUS_EMAIL_WEBHOOK_TOKEN`
- `CKNEXUS_ACCESS_TOKEN`
- `CKNEXUS_DOMAIN`

`OPENAI_API_KEY` is required only when Live Mode is enabled. Other integration credentials are
optional unless the corresponding integration is enabled. Use the variable names and defaults
in `docker-compose.prod.yml` as the authoritative runtime contract.

## 3. Staging validation

Use a dedicated staging environment and its own database/credentials:

```bash
docker compose --env-file /secure/path/cknexus-staging.env \
  -f docker-compose.p0.yml up -d --build
curl -fsS http://127.0.0.1:8000/health
```

Do not expose port 8000 directly to the public internet. Apply the approved edge proxy and
access policy. Do not point staging at production volumes or credentials.

## 4. Production deployment

After the release gates and exact-subject evidence are approved:

```bash
docker compose --env-file /secure/path/cknexus.env \
  -f docker-compose.prod.yml up -d --build
curl -fsS https://your-domain.example/health
```

The environment file is external to the repository. Do not print it or pass secret values on
the command line. Preserve database volumes and evidence during upgrades and rollback.

## 5. Local development

```bash
cp .env.example .env.local
./start.sh
```

`start.sh` delegates to `start_unified.sh`, which launches:

```bash
.venv/bin/python -m creator_app.unified
```

The installed `ck-nexus` command and `python main.py` are compatibility interfaces to the same
runtime. Do not launch `creator_app.api:create_app` directly for a deployed CK-NEXUS instance.

## 6. systemd deployment

The systemd unit must use the same module entry point as Docker and local development:

```ini
ExecStart=/opt/cknexus-creator-venv/bin/python -m creator_app.unified
```

Keep environment values in the configured external `EnvironmentFile`; keep the service bound
to loopback unless an explicitly reviewed reverse-proxy topology requires otherwise.

## 7. Health and release verification

- `GET /health` — liveness/readiness endpoint.
- `GET /api/control/manifest` — unified control-plane inventory (when authorized/configured).
- `python3 scripts/release_check.py` — local release checks.
- CI evidence must be bound to the exact commit, tree, and release-subject manifest.

A successful local test or container health check is not, by itself, production approval.
Missing or mismatched evidence remains `BLOCKED` or `NOT_VERIFIED`; never promote a release by
rewriting evidence or bypassing the canonical gates.
