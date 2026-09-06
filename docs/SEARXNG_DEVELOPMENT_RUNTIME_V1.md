# CK-NEXUS SearXNG Development Runtime V1

Status: Post-P0 development candidate.
Network posture: loopback-only by default.
Production effect: none.

## Purpose

This package provides a self-hosted SearXNG discovery runtime for the
CK-NEXUS Global Knowledge discovery adapter.

SearXNG remains a discovery provider. Search results are not VERIFIED
evidence and do not bypass CK-NEXUS filtering, provenance, crawl policy,
coverage, contradiction, or human-review gates.

## Current upstream alignment

The runtime follows current SearXNG administration guidance:

- containerized Compose deployment,
- local `settings.yml`,
- `use_default_settings: true`,
- limiter enabled,
- Valkey backing for limiter features,
- JSON added explicitly to `search.formats`,
- `SEARXNG_SECRET` and `SEARXNG_BASE_URL` supplied by environment.

## Files

- `deploy/searxng/docker-compose.yml`
- `deploy/searxng/settings.yml`
- `deploy/searxng/limiter.toml`
- `deploy/searxng/.env.example`
- `scripts/searxng_doctor.py`

## Setup

Create a local runtime directory from the repository files and copy the
example environment file:

```bash
cp deploy/searxng/.env.example deploy/searxng/.env
```

Generate a random secret outside source control and place it in the local
`.env` file. Do not commit the generated secret.

Start the development runtime:

```bash
cd deploy/searxng
docker compose up -d
```

The default port binding is loopback only:

`127.0.0.1:8080:8080`

Do not expose the development instance directly to the public internet.

## JSON readiness check

After the service is healthy:

```bash
python scripts/searxng_doctor.py --base-url http://127.0.0.1:8080/
```

The doctor requires:

- HTTP 200,
- `application/json` content type,
- a JSON object root,
- a `results` array.

A failed check means CK-NEXUS must keep the provider unavailable.

## Security boundaries

The runtime does not provide or authorize:

- CAPTCHA solving,
- paywall bypass,
- credential replay,
- robots or terms bypass,
- Production database access,
- automatic VERIFIED promotion.

The Compose network does not publish Valkey. SearXNG itself is published only
on loopback in the development default.

## Image pinning

The example uses configurable image tags for development convenience.
Before an adoption or release candidate, resolve and pin reviewed immutable
image digests and record them in development evidence.

## Rate limiting

SearXNG's limiter is enabled and backed by Valkey. The development
`limiter.toml` passlists only loopback addresses because the Compose port is
also bound only to loopback. This permits the local CK-NEXUS doctor/adapter
without disabling the limiter or opening a private-network exemption.

CK-NEXUS must still retain its own caller-side rate and concurrency limits.
Upstream engines can impose their own limits independently of the local
SearXNG limiter.

## Evidence

A successful doctor result proves only that the JSON discovery endpoint was
reachable at the observed runtime. It does not prove correctness of search
results, source independence, or release readiness.
