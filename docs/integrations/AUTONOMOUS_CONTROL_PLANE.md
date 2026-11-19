# CK-NEXUS Autonomous Multi-Agent Control Plane

CK-NEXUS now has a thin control-plane seam that composes existing AI Team, development-assistant routing, parallel execution, sandbox, verification, MCP, and evidence components instead of introducing another agent framework.

## Flow

```text
@ai / user request
    -> cknexus_auto_dispatch
    -> ControlPlaneOrchestrator.plan()
    -> bounded TaskGraph
    -> existing TeamDirector / worker handlers
    -> existing execution/sandbox boundary
    -> verification + security
    -> evidence
```

## Safety contract

- Planning is explicitly `PLANNED_NOT_EXECUTED`.
- Plans are `NO-GO` for production and never grant external mutation authority.
- The control plane does not apply or commit assistant patches.
- Parallel work only runs for dependency-ready nodes.
- Failed dependencies block downstream nodes.
- Repair attempts are bounded by `ControlPlaneVerifier.max_repairs`.
- `EXECUTED_UNVERIFIED` can become release evidence only after test and security verification succeed.
- The existing CK-NEXUS execution kernel remains the authority for sandboxed execution, credentials, approvals, idempotency, kill switches, and evidence.
- MCP remains loopback-only; remote access must use the authenticated tunnel/boundary already established for CK-NEXUS.

## Current MCP behavior

`cknexus_auto_dispatch(..., mode="auto")` keeps the existing normal-question provider path. Development requests continue to expose the legacy `plan` output for compatibility and now also return a `control_plane` task graph. The graph is descriptive until an authorized execution path is explicitly invoked.

`cknexus_autonomy_status()` provides one inventory-only probe for installed local workers, redacted provider health, and role-to-worker routing. It does not execute a worker or expose secret values. Routing candidates are filtered to assistants that are actually installed and advertise at least one required capability; unavailable assistants are not presented as runnable candidates. Research, implementation, verification, and security use capability labels from the maintained assistant registry rather than invented role labels.

## Fast-path routing rules

- Prefer a single relevant tool call over sequentially probing every subsystem.
- Run independent read-only probes in parallel where supported.
- Use only verified installed workers for routing; empty candidates mean a capability gap, not permission to install a new framework automatically.
- Use the existing MCP, TeamDirector, execution kernel, sandbox, test/security gates, and evidence system. Do not bypass them for speed.
- Keep external sends, production changes, merges, and credential changes behind explicit approval.

## OpenClaw

The OpenClaw skill should call `cknexus_auto_dispatch` when an authenticated MCP connection exists. OpenClaw native auto-invocation is not considered operational until its Gateway passes a real MCP invocation test.
