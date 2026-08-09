# R14 NOTICE

> n8n is retired from the active CK-NEXUS runtime. Any n8n instructions below are historical R4-R13 material and must not be used for R14 deployment. Use `docker-compose.p0.yml` / `docker-compose.prod.yml` as the current source of truth.

# CK-NEXUS P0 VPS Quickstart

This kit is for an isolated **staging VPS**, not production. Runtime evidence is required before promoting the product from Early Access RC to GA.

## 1. Install Docker

```bash
sudo ./scripts/vps/install_docker_ubuntu_debian.sh
```

## 2. Generate staging secrets

```bash
sudo ./scripts/vps/generate_staging_env.sh /etc/cknexus/cknexus-p0.env
sudo editor /etc/cknexus/cknexus-p0.env
```

Fill `CKNEXUS_SOURCE_COMMIT` with the immutable Git SHA. `OPENAI_API_KEY` can remain empty until P0-AI-001.

## 3. Phase 0 bring-up

```bash
./scripts/vps/phase0_bringup.sh /etc/cknexus/cknexus-p0.env
```

The command starts PostgreSQL, runs both migrations, builds FastAPI, starts n8n, checks `/health`, verifies required tables, records versions/image digests, and writes SHA-256 evidence under `/var/tmp/cknexus-evidence`.

## 4. Run P0 v3

```bash
./scripts/vps/run_p0_v3.sh /etc/cknexus/cknexus-p0.env
```

For destructive restore drills, use an isolated target and explicitly pass the runbook's destructive flag only after the backup gate harness has been configured.

## Network rule

App and n8n bind to `127.0.0.1` only. Put TLS/reverse proxy/VPN in front before exposing either service. The compose file has no `host.docker.internal` dependency, so it works on native Linux VPS hosts.

## n8n

The staging baseline is `n8nio/n8n:2.32.6`; capture the resolved image digest in evidence and pin the digest for the final delivery build after validation. Run `n8n audit` on the exact staging instance as part of P0-SEC-001.
