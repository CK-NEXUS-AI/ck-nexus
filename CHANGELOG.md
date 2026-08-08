# Changelog

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
