# CK-NEXUS Installation Guide — Docker on Ubuntu/Debian

## 1. Requirements

- 64-bit Linux host with Docker Engine and Compose plugin
- Recommended starting point: 4 CPU / 8 GB RAM
- Persistent storage for CK-NEXUS PostgreSQL, n8n PostgreSQL and backups
- TLS reverse proxy for any internet-facing endpoint
- Customer-controlled OpenAI API project/key for Live Mode
- Customer-controlled email/OAuth or SMTP credentials when Email Gateway is enabled

## 2. Secrets

Keep the runtime environment file outside the repository, restrict it to the service owner (`chmod 600`), and never include API keys/OAuth tokens in a customer delivery ZIP, screenshots, logs or support tickets.

Minimum secrets include:

- `CKNEXUS_DB_PASSWORD`
- `N8N_DB_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `CKNEXUS_ACCESS_TOKEN`
- `CKNEXUS_EMAIL_WEBHOOK_TOKEN`
- `OPENAI_API_KEY` when Live Mode is enabled

## 3. Start in staging first

```bash
docker compose --env-file /secure/path/cknexus.env -f docker-compose.prod.yml up -d --build
curl -fsS http://127.0.0.1:8000/health
```

Do not expose ports 8000 or 5678 directly to the internet. Put them behind a TLS reverse proxy and access policy.

## 4. n8n

The default RC uses a **customer-owned n8n instance**. CK-NEXUS does not sublicense n8n. Review the current n8n license for the actual use/distribution model before sale or deployment.

Bind customer credentials inside n8n. Run its security audit on the exact staging instance:

```bash
docker compose --env-file /secure/path/cknexus.env -f docker-compose.prod.yml exec -T n8n n8n audit
```

Retain the audit report as P0 evidence. Re-check the stable n8n release/security advisories before each GA delivery. The RC compose defaults to 2.32.6 unless `N8N_IMAGE`/version policy is changed deliberately.

## 5. OpenAI Live Mode

The RC default model is `gpt-5-mini`, intended for cost-sensitive workloads. Confirm model access in the customer's OpenAI project. Use the production application path for final smoke evidence rather than relying only on a standalone API call.

## 6. P0 Runbook

Run only in isolated staging first:

```bash
export CKNEXUS_SOURCE_COMMIT=<exact-commit-sha>
export CKNEXUS_EVIDENCE_ROOT=/secure/evidence
python runbooks/p0_runbook_v3.py --env-file /secure/path/cknexus.env
```

Destructive restore tests require an isolated environment and explicit enablement. Missing prerequisites must remain `BLOCKED`, never `PASS`.
