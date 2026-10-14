# CK-NEXUS Security / Runtime Follow-up

- Captured at (UTC): 2026-10-14T21:10:28Z
- Repository: https://github.com/CK-NEXUS-AI/ck-nexus
- Audit branch: `audit/20261014-readonly-baseline`
- Parent branch commit at capture: `444bf75ca0abd685e58b74251a1e1c2f4131cf50`
- Method: read-only GitHub API/CLI, read-only service metadata, and n8n MCP metadata/execution queries.
- No security setting, workflow, credential, service, or production configuration was changed. No n8n workflow was executed by this audit.

## GitHub security features and alert evidence

- Repository metadata reports: code security enabled; Dependabot security updates enabled; secret scanning enabled; secret scanning push protection enabled.
- The queried code-scanning alerts endpoint returned HTTP 404 with `no analysis found`. Therefore, the current API result does not establish a completed Code Scanning analysis for this repository. Do not interpret it as zero vulnerabilities.
- Secret-scanning alerts endpoint returned an empty list (0 alerts) in the queried response.
- Dependabot alerts endpoint returned an empty list (0 alerts) in the queried response.
- Codex CLI is present as `codex-cli 0.162.1`; its login status reports an API-key login. This audit did not launch a Codex Security scan, and no key/token value is recorded here. Historical Q10 artifacts still say NOT_VERIFIED/BLOCKED; authentication alone does not close Q10.

## Current VPS service and listener evidence

- `cknexus-api-gateway.service`: active/running; service user `cknexus-gateway`; `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`.
- `cknexus-scanner.service`: active/running; service user `root`; `NoNewPrivileges=yes`, but `ProtectSystem=no`, `ProtectHome=no`, `PrivateTmp=no` in the inspected unit properties. This is a hardening review finding, not a change request executed by this audit.
- Both units expose broad `CapabilityBoundingSet` values in the inspected metadata. Review and reduce capabilities to the minimum needed in a separately controlled change window; do not edit the service automatically from this evidence alone.
- Health HTTP status at capture: 5678=200 (n8n), 8787=200 (scanner), 8790=200 (API gateway), 18789=000 (no responding OpenClaw health endpoint).
- Port 8790 is loopback-bound and owned by a `python3` process. The correct systemd unit is `cknexus-api-gateway.service`; a prior query of the different name `cknexus-gateway.service` was inactive.
- `/opt/cknexus` is not a Git worktree in this inspection. Do not treat it as the canonical source checkout.

## n8n Cloud workflow evidence

The n8n2 MCP search returned six CK-NEXUS workflows. This is metadata only; the audit did not execute any workflow.

- `vPc9I9AICVGaeXEK` — Hotmail 7-Day Read-Only Diagnostic — inactive.
- `ASq906OfEaDqjDqGug` — Control Plane - Production Error Alert — listed active by search, but detail and execution lookups returned `Workflow not found or you don't have permission to access it`. This is an unresolved access/identity discrepancy; it does not prove the workflow is broken.
- `QYr9oAO6hWv5QcT9` — Operations Master - Safe Orchestrator — inactive.
- `DX6ROxvvgE0iU7K5` — AI Ops Radar - Daily Digest — active. Execution metadata showed previous successful runs #74 and #73 on 2026-10-13 and a prior error run #49 on 2026-10-11. No new execution was started.
- `DNY1Ta0KuZumRxAV` — CK-NEXUS Evidence Gate — active.
- `tOsg3K1xcrxI1GOM` — Evidence Gate Helper — active.

## Gate decisions

- Q10: NOT_VERIFIED — security features are enabled, but a Code Scanning analysis was not found and this audit did not execute Native Codex Security.
- Q11: BLOCKED / NOT_VERIFIED — live secure credential injection and authorized provider execution were not verified by this audit.
- Q12: NOT_VERIFIED — active runner service is not proof of kernel-enforced resource limits or sandbox isolation.
- OpenClaw: NOT_VERIFIED — no responding health endpoint at port 18789.
- n8n production error alert workflow: ACCESS/IDENTITY DISCREPANCY — search sees metadata but details/executions are denied or not found.
- Production: NO-GO.

## Follow-up actions

1. Run the required Native Codex Security scan when the supported security capability/quota is available; bind it to the canonical commit and preserve raw evidence safely.
2. Audit scanner systemd capabilities and hardening; prepare a least-privilege patch for review without applying it in this audit.
3. Establish why the n8n connector can search the production error-alert workflow but cannot retrieve its details/executions; verify identity/project/ownership without triggering it.
4. Prove Q11 secure credential injection and Q12 kernel-enforced sandbox limits using controlled tests.
5. Reconcile Q13-Q16 evidence with the same release identity.

## Interpretation

HTTP 200 is health evidence only. Empty alert lists are not a substitute for a completed scan. Service active is not sandbox verification. Workflow search visibility is not execution permission. This report is an unsigned audit note, not a release attestation.
