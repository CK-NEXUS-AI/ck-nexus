# CK-NEXUS Development Assistant Execution Contract V1

Status: Post-P0 development only. Production remains NO-GO.

## Goal

Prepare external developer assistants for fast parallel work without granting
those assistants authority, raw credentials, arbitrary shell access, or direct
production mutation rights.

## Boundary

The contract package is intentionally non-executing. It produces deterministic
execution envelopes that a separate CK-NEXUS sandbox executor must enforce.
This separates planning from execution and keeps the execution authority inside
CK-NEXUS.

Default controls:

- disposable worktree isolation
- network denied unless explicitly brokered
- read-only source baseline
- patch-only output
- bounded timeout and output size
- opaque `cred://` credential references only
- no external mutation authority
- development evidence is never release evidence

## Flow

1. CK-NEXUS selects an approved active assistant.
2. `ExecutionRequest` normalizes the task, workstream and capability needs.
3. `DevExecutionContract` verifies assistant state and capability coverage.
4. A deterministic `devexec-*` identity and request SHA-256 are created.
5. The contract returns `PLANNED_NOT_EXECUTED` plus sandbox requirements.
6. A separately reviewed sandbox executor may later consume that plan.
7. Provider output must return as patch/artifact digests and redacted evidence.
8. Independent CK-NEXUS verification decides whether any candidate change is
   accepted into the repository.

## Evidence

`ExecutionEvidence` stores only execution identity, assistant identity, result
state, exit code and SHA-256 digests. It does not embed raw stdout, stderr,
patches or secrets. The evidence envelope itself receives a deterministic
SHA-256 digest for append-only audit storage.

## MCP

The development MCP server exposes `cknexus_dev_execution_plan`. The tool only
builds a plan. It does not invoke a CLI, open a shell, install software or write
to external systems.

## Next phase

A future executor implementation may be added only after independent review of:

- disposable worktree/container lifecycle
- command allowlists per assistant
- filesystem mount policy
- network egress policy
- credential broker integration
- output truncation and redaction
- patch provenance
- independent verification
- append-only evidence identity

No executor may bypass CK-NEXUS policy, approval, credential or evidence gates.
