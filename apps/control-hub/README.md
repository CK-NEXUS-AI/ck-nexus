# CK-NEXUS Control Hub Prototype

This folder is the professional Unified Command Center prototype for CK-NEXUS.

## Purpose

The prototype validates information architecture, operator control, accessibility patterns and responsive behavior before runtime migration.

It is intentionally side-effect free. The only live calls it attempts are read-only GET probes to `/health` and `/api/integrations/status` when served from a CK-NEXUS runtime. If those endpoints are unavailable, the shell remains usable as a prototype and labels the runtime as unbound.

## Run locally as a static prototype

From this directory, use any local static HTTP server. Opening the file directly may block fetch behavior depending on browser security policy.

## Current surfaces

- global environment/release posture
- system metrics
- active AGNES work table
- pending approval review
- connector health
- Q01-Q16 gate strip
- event timeline
- contextual inspector
- goal/command dialog
- responsive navigation

## Safety boundaries

- no POST/PATCH/PUT/DELETE requests
- no OAuth initiation
- no credential values
- no production mutation
- no real approval mutation
- no release promotion

## Quality targets

See:

- `docs/architecture/UNIFIED_COMMAND_CENTER_UX.md`
- `docs/architecture/WEB_QUALITY_GATES.md`

Target standards include WCAG 2.2 AA, WAI-ARIA practices where native HTML is insufficient, current Core Web Vitals, OWASP ASVS 5.0 and OWASP web security guidance.

## Next implementation lane

After Q10 is legitimately complete, evolve this shell into an API-bound application in phases:

1. read-only operational state
2. authenticated identity/workspace shell
3. approval read path
4. event/evidence explorer
5. policy-bound write actions
6. AGNES live execution controls
7. recovery/incident center

Each write capability must be authorized by backend governance. Hiding or disabling a button is never an authorization boundary.
