# Changelog

## 0.2.0 R7 — Credential Broker & Provider Cutover

- Added a least-privilege Credential Broker with consumer-bound leases, explicit credential policy, ephemeral runtime secrets, and redacted status surfaces.
- Added concrete Mock, loopback-only Ollama, and broker-backed OpenAI provider adapters.
- Connected the R6 Provider Router to CreatorRuntime and the Development Council while preserving bounded attempts, circuit breaker state, local-first policy, and production fail-closed behavior.
- Added Gmail OAuth server flow with one-time state, read-only default scope, optional send scope, and broker-only token storage.
- Added GitHub App JWT / installation-token path with short-lived token storage and no token returned from API status/actions.
- Added `/api/providers/status`, `/api/security/credentials/status`, Gmail OAuth endpoints, and GitHub App status/token endpoints.
- Disabled sensitive payload capture in OpenAI Agents SDK traces for CreatorRuntime and Development Council runs.

## 0.2.0 R5 — Development Council

- Added CK-NEXUS Lead Orchestrator with five advisory specialist agents: Architect & Strategist, Research & Analyst, Product & UX Designer, Engineering & Automation Builder, and Security / QA / DevOps Reviewer.
- Added manager-style Agents-as-tools orchestration, focused consult modes, shared conversation sessions, and a narrow hosted web-search surface available only to the Research adviser.
- Added `GET /api/dev-team` and `POST /api/dev-team/run`, Demo Mode behavior, access/rate-limit reuse, per-adviser model override slots, documentation, tests, and a DEV TEAM workspace in `/demo`.
- Kept all five advisers advisory-only; real mutations remain behind separately gated execution paths.

## 0.2.0

- Added an optional, disabled-by-default Codex CLI bridge for trusted local engineering tasks.
- Added access-token enforcement, fixed workspace configuration, safe sandbox choices, timeouts,
  output caps, and secret-bearing environment filtering for Codex tasks.
- Added Codex status/task API endpoints, tests, and integration documentation.

## 0.1.0 — 2026-08-05

- Introduced CK-NEXUS Creator Edition as the primary sellable MVP path.
- Added four menu-selected creator agents using the OpenAI Agents SDK.
- Added responsive Thai web UI, local SQLite run history, and session memory.
- Added a typography-first Control Hub with three themes, text-based status, masked/type reveal, magnetic hover, kinetic mesh depth, and reduced-motion support.
- Added a text-only command palette, real history metrics with number ticker, text output download, and local-session deletion controls.
- Added Demo Mode, optional bearer protection, input limits, rate limiting, security headers, Docker support, automated tests, release checks, and commercial-delivery templates.
- Added security, test, release-status, and UX design-system reports.
- Preserved the original SaaS Billing module as an optional package extra.

R13 AGNES Skill Nervous System: development candidate; see docs/R13_AGNES_SKILL_NERVOUS_SYSTEM.md

## R24 — Council Capability Authority Hardening

- Added one Python policy authority for Council capability enforcement.
- Added signed service identity; callers cannot self-assert agent identity.
- Added verified evidence registry and source-evidence quality checks.
- Added parameter-bound, signed, one-time execution grants.
- Reused the existing CK-NEXUS Credential Broker through a scope adapter; no second secret store.
- Added transactional budget accounting and admin-gated top-up capability.
- Added authorized safety veto and fail-closed human-review arbitration.
- Added hash-chained audit records and authenticated transcript access.
- Added thin Node.js capability client with zero policy logic.
- Added a required release gate and regression tests for authority invariants.

## R24 — Council Capability Authority Hardening
- Added authenticated single-authority Council capability enforcement.
- Added verified evidence registry and params-bound signed one-time grants.
- Reused the existing Credential Broker through a scope adapter.
- Added transactional budgets, authorized safety veto, hash-chained audit, and a thin Node client.
- Added a required Council capability release gate.

## R28 Universal Auto Connector Fabric (development candidate)
- Added MCP 2026-07-28 stateless discovery client with pagination, cache metadata, required request metadata and mirrored HTTP method/name headers.
- Added OpenAPI 3.x discovery and schema normalization.
- Added persistent connector registry, conservative risk classifier, model-neutral namespaced tool binding, SSRF-oriented endpoint validation, bounded no-redirect transport, and hash-chained connector evidence.
- Added Creator API registration/discovery/activation/read endpoints. Connector execution remains fail-closed and is not publicly exposed until Policy Authority integration is complete.
