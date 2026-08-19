# CK-NEXUS Release Candidate Admin Guide

Status: Release Candidate administration guidance only.

## Authority and release identity

Administrators must pin deployments and verification to the canonical release subject. Do not substitute `main` or another development branch for the frozen release source without performing a subject rotation and restarting closure at Q10.

## Secrets

- Never commit provider/API secrets to the repository.
- Store the Q11 staging `OPENAI_API_KEY` only in GitHub Actions secrets for the exact verifier.
- Keep secret values out of logs, artifacts, issue comments and release manifests.
- Use CK-NEXUS credential broker/vault paths where the application supports them.

## Access control

Set `CKNEXUS_ACCESS_TOKEN` before exposing protected application APIs. Email gateway deployment additionally requires its dedicated webhook token. Integrations should remain disabled unless their required credentials and policies are configured.

## Runtime safety

The runtime installs security headers, request-size controls, rate limiting and correlation/observability middleware. Do not remove these controls as a deployment shortcut.

## Q12 host class

Production-closure verification requires a self-hosted Linux Actions runner labeled `cknexus-q12`, operating as non-root, with a pre-delegated writable cgroup v2 subtree exposing `cpu`, `memory` and `pids`. See `Q12_SELF_HOSTED_RUNNER.md`.

## Evidence operations

Committed release evidence is immutable input to the provenance verifier. Never edit a status field from BLOCKED to PASS manually. PASS evidence must originate from the required verifier and reconcile to GitHub Actions artifact ID, server-side digest, run ID, repository identity and verifier branch.

## Backup and recovery

The current closure line includes PostgreSQL backup/isolated restore candidate evidence. Treat the exact production database backup policy, retention, encryption, restore frequency and disaster-recovery objectives as deployment-specific configuration that must be documented for each customer environment.

## Production promotion

Do not mark PR #14 ready, merge it, create a Production Ready tag or deploy production until the final package workflow has both provenance PASS and an actual successful package artifact with a verified checksum.
