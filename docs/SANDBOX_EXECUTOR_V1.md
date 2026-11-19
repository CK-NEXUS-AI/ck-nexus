# CK-NEXUS Sandbox Executor V1

Status: Post-P0 development infrastructure only. Production remains NO-GO.

## Purpose

Sandbox Executor V1 is the narrow execution kernel for development assistants. It consumes a
previously approved `DevExecutionContract` plan and can run one CK-NEXUS adapter image inside a
disposable container. Provider/model assistants remain workers; CK-NEXUS remains authority.

The executor never applies a generated patch, never commits it, never pushes it, and never turns
an execution result into release evidence. A zero exit code produces `EXECUTED_UNVERIFIED`, not
`VERIFIED`.

## V1 containment contract

The executor requires all of the following before a provider process can start:

- POSIX host and non-root UID.
- Exact 40-character Git source SHA.
- Disposable Git worktree created from that exact SHA.
- Docker or Podman only.
- Adapter image pinned by immutable `@sha256:<digest>` reference.
- `--pull=never`; unknown images are not downloaded automatically.
- Network disabled with `--network=none`.
- Read-only container root filesystem.
- All Linux capabilities dropped.
- `no-new-privileges` enabled.
- PID, memory, CPU, timeout, and patch-size bounds.
- Host user UID/GID propagated to the container; root execution is refused.
- No Docker socket or privileged mount.
- No credential resolution or credential forwarding in V1.
- Task delivered on stdin rather than interpolated into a shell command.
- Fixed adapter entrypoint `/cknexus/adapter`.
- Patch captured from the disposable worktree and bounded before being returned.

## Adapter image contract

A development assistant image is not trusted merely because it exists. Before use it must be
reviewed separately and referenced by immutable image digest. The image must provide:

```text
/cknexus/adapter
```

The adapter reads the task from stdin, operates only inside `/workspace`, and exits with a normal
process exit code. It must not expect network access or runtime credentials in V1.

The executor intentionally uses `--pull=never`; installing or downloading an assistant is a
separate governed acquisition/quarantine process.

## Execution states

```text
PLANNED_NOT_EXECUTED
        |
        v
CONTAINER EXECUTION
        |
        +--> EXECUTION_FAILED
        |
        v
EXECUTED_UNVERIFIED
        |
        v
INDEPENDENT VERIFIER (separate phase)
        |
        +--> REJECTED
        |
        v
VERIFIED DEVELOPMENT PATCH
```

`VERIFIED DEVELOPMENT PATCH` is still not production or release evidence.

## Example Python flow

```python
from pathlib import Path

from creator_app.dev_assistants import (
    DevExecutionContract,
    ExecutionPolicy,
    ExecutionRequest,
    IsolationMode,
    NetworkMode,
)
from creator_app.sandbox_executor import SandboxExecutionInput, SandboxExecutor

request = ExecutionRequest(
    assistant_id="aider",
    task="Inspect this exact checkout and produce a minimal patch.",
    workstream_id="ws-example",
    required_capabilities=("code_edit",),
)
policy = ExecutionPolicy(
    isolation=IsolationMode.DISPOSABLE_CONTAINER,
    network=NetworkMode.DENY,
)
plan = DevExecutionContract().build_plan(request, policy)

result = SandboxExecutor().execute(
    SandboxExecutionInput(
        plan=plan,
        repository_path=Path("/srv/ck-nexus"),
        source_sha="<exact-40-char-git-sha>",
        image_ref="registry.example/cknexus/aider-adapter@sha256:<64-hex-digest>",
    )
)

assert result.patch_applied is False
assert result.release_evidence is False
```

Do not place a real credential in the plan or environment. V1 rejects all credential references
and all brokered network requests. Those capabilities require a separately reviewed brokered
network/credential adapter.

## Evidence boundary

The executor returns a redacted `ExecutionEvidence` envelope containing execution identity,
assistant identity, state, exit code, and patch digest. Raw provider stdout/stderr are discarded.
The patch itself is a development artifact and must be independently verified before application.

## Production boundary

This component does not promote Q10, Q11, or Q12; does not by itself satisfy the Q10 open-source layered security gate;
and does not authorize merging PR #14. Production remains NO-GO until the independent production
closure requirements pass on their exact subjects.
