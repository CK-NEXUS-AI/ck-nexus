# R14 NOTICE

> n8n is retired from the active CK-NEXUS runtime. Any n8n instructions below are historical R4-R13 material and must not be used for R14 deployment. Use `docker-compose.p0.yml` / `docker-compose.prod.yml` as the current source of truth.

# CK-NEXUS v0.2.0 — P0 VPS RC Patch Notes

Status: **P0 staging-ready package; not a Production PASS.**

## Fixed for VPS Phase 0

- `docker-compose.p0.yml` now uses PostgreSQL for both Creator runtime history and Email Gateway.
- Added one-shot `migrate` service that applies `001_email_gateway.sql` and `002_creator_runs.sql` before FastAPI starts.
- Dockerfile now includes top-level `migrations/`, required by the PostgreSQL Creator store initialization path.
- n8n staging baseline pinned to `n8nio/n8n:2.32.6`; final release should record the resolved image digest.
- App and n8n remain bound to `127.0.0.1`; expose only through a TLS reverse proxy/VPN.
- P0 runbook defaults to `docker-compose.p0.yml` and records PostgreSQL/n8n/Python versions in evidence.
- Security gate now uses the same P0 compose/env file as the runbook.
- Added Ubuntu/Debian VPS Docker installer, secure environment generator, Phase-0 bring-up/evidence collector, and P0 runbook wrapper.

## Local regression evidence

- Core Creator + Email Gateway regression subset: `26 passed`.
- Local SQLite duplicate-concurrency guard: `100 attempts -> 1 winner -> 1 journal row`.
- Compose YAML and shell/Python syntax validated locally.

These local results do **not** promote production gates. PostgreSQL concurrency, real n8n executions/audit, provider timeout, SIGKILL recovery, restore/boot, OpenAI live path, alert delivery and clean-machine evidence must be produced on staging.
