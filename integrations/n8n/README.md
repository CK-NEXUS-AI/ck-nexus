# CK-NEXUS n8n Development Agent Fabric

Development-only automation layer for CK-NEXUS. It is intentionally separated from the production-closure subject and must not be used to promote Q10/Q11/Q12.

## Roles

- Orchestrator — decomposes work and consolidates evidence.
- Researcher — gathers authoritative public sources and implementation references.
- Architect — designs interfaces, invariants, migrations and failure boundaries.
- Builder — produces development-only code/patch proposals.
- Verifier — runs independent tests and evidence checks.
- Security Reviewer — checks secrets, trust boundaries, injection, privilege and supply-chain risk.

## Authority boundary

CK-NEXUS Governor remains authoritative for state, permissions, policy and execution. n8n coordinates work but cannot self-approve production mutation. `main`, `release/q10-q16-closure`, PR #14, merge, production deploy, production tags, raw-secret access and Q10 promotion without native Codex Security evidence are denied.

## Runtime contract

The importable workflow receives `POST /webhook/ck-nexus/dev-agent`. It validates a development branch prefix, fans the request into six specialist roles, calls `CK_NEXUS_AGENT_ENDPOINT`, consolidates results and marks them unverified until an independent check succeeds.

`CK_NEXUS_AGENT_ENDPOINT` must be supplied by runtime configuration. No API key is stored in this repository or workflow.

## Windows development install

Use `install_n8n_windows.ps1`. The installer pins n8n 2.35.7, uses the existing pinned Node toolchain, imports the workflow and binds n8n to `127.0.0.1:5678`. `start_n8n_dev.ps1` starts the local development instance.

The Windows instance is for development automation only. Q12 still requires the dedicated non-root delegated-cgroup-v2 Linux verifier environment.

## Production safety

This fabric must never be interpreted as Q10/Q11/Q12 evidence. Q10 requires the native Codex Security Deep Security Scan; Q11 and Q12 must use their authoritative exact-subject verifier workflows after Q10 passes.
