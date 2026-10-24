# Tool 09 — Hive (Hive Commons)
Research date: 2026-10-25. Primary sources: https://github.com/hivecommons/hive, https://docs.hivecommons.dev/docs/hive/agent-configuration, https://github.com/hivecommons/hive/blob/main/src/docs/acmm-policy-matrix.md.

## 1. Identity
Hive is an open-source co-maintainer/orchestration system for GitHub projects, developed by Hive Commons. The repository and docs describe a configurable agent fleet, an ACMM (AI Codebase Maturity Model) with six autonomy levels, and hosted hub options. Verify the exact license from the current repository LICENSE before deployment; this report does not infer license from open-source availability alone. The project is active and documents Docker Compose, Podman and Kubernetes deployment paths.

## 2. Category
Multi-Agent orchestration, with configurable autonomy from advisory to automatic merge. ACMM Level 6 is a policy setting, not a universal capability score or proof that an arbitrary repository is safe for full autonomy.

## 3. Core Mechanism
Hive watches repository work queues—issues, PRs, failing CI and security/dependency alerts—and launches short-lived agents for bounded work. Its docs emphasize fresh context per task, external context in repository/knowledge/audit records, and deterministic prompt templates built from issue/CI/diff/trust facts. A Go control plane, authenticated Node gateway, terminal access and deterministic filters/gates govern agent activity. ACMM profiles define roster, cadence and merge policy; level 6 can auto-merge when checks pass while cross-repository outreach remains held. These are system design claims from project documentation, not an independent security certification.

## 4. Key Capabilities
- Repo maintenance loop from issue/CI signal to triage, fix, review and release.
- ACMM levels allow incremental adoption rather than jumping directly to full autonomy.
- Short-lived agent contexts reduce long-running drift.
- Deterministic policy filters, scoped tokens, proxy enforcement and human-owned audit trail.
- Multiple coding backends can be routed to by workflow.
- Operator dashboard and CLI for agent state, spending and pause/resume controls.

## 5. Evidence
The official repository documents architecture, policy levels and installation. The specific claims in the requested brief—YAML profile spawning, “six types of suffering,” Hive Coder meta-agent, 74 CI/CD workflows, 32 nightly suites, and bug-to-fix under 30 minutes—were not all independently corroborated by the sources located in this pass. Mark those metrics `No public evidence` until the exact commit, CI logs and measurement method are supplied. A closest verifiable proxy is the repository's documented six-level ACMM and workflow policy matrix; it does not validate the other numeric claims.

## 6. Limitations
An orchestration layer can make mistakes repeatable at scale. Auto-merge depends on the quality of CI, test coverage, secret isolation, token scopes and deterministic gates. Short-lived agents still face prompt injection from repository content and untrusted issues. “Green CI” is only meaningful if tests are resistant to tampering and the acceptance criteria are independent of the agent that wrote the patch. Multi-agent concurrency can create duplicate PRs or race conditions without deduplication and locking.

## 7. Cost & Access
The project provides self-host deployment paths; compute, LLM usage, storage and operational maintenance are not necessarily free. Hosted hub availability and pricing should be checked on the official site. Agent backends may require their own subscriptions or API keys. Source: https://github.com/hivecommons/hive and https://docs.hivecommons.dev/. No claim of fully free inference should be made merely because the orchestrator is open-source.

## 8. Comparison
Compared with Captain Claw, Hive is focused on repository maintenance, CI and maturity-gated autonomy; Captain Claw is a broad specialist-agent command center. Compared with OpenHands Control Plane, Hive's public repository emphasizes repo-specific co-maintenance and ACMM profiles, while OpenHands positions itself as a broader enterprise control plane across agent stacks.

## 9. Verdict
Worth a controlled proof of concept if CK-NEXUS needs continuous issue/CI maintenance and explicit autonomy levels. Start at advisory or quality-gated mode, not Level 6. Require signed evidence, branch protections, secret scanning, test-locking, budget caps, audit logs and manual promotion after a measured trial.

## Evidence gaps
The requested CI/nightly suite counts and <30-minute fix claim remain unverified here. Do not repeat them as fact without pinned artifacts and independent reproduction.
