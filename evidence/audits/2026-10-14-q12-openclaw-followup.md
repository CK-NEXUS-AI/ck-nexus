# CK-NEXUS Q12 / OpenClaw Follow-up

- Captured at (UTC): 2026-10-14T21:10:57Z
- Repository: https://github.com/CK-NEXUS-AI/ck-nexus
- Audit branch: `audit/20261014-readonly-baseline`
- Parent branch commit at capture: `12d80405d4796c5922c5d24733840ebcf969f979`
- Method: read-only cgroup v2, systemd, package-lock metadata, process, and resource checks.
- No services were restarted, no package was installed, and no configuration was changed.

## Q12 runner and cgroup enforcement

- GitHub Actions Runner service `actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service` was active/running.
- Inspected service properties included `Delegate=yes`, `NoNewPrivileges=no`, `ProtectSystem=no`, `ProtectHome=no`, and `PrivateTmp=no`. The `User` property was unset in systemd metadata; the effective service identity should be verified before any remediation.
- The delegated cgroup `/sys/fs/cgroup/cknexus-delegated` exists and exposes CPU, memory, and PID controllers, but current values are unbounded: `cpu.max=max 100000`, `memory.max=max`, `pids.max=max`.
- Therefore, the presence of the cgroup directory/controllers does not prove resource enforcement. Q12 remains NOT_VERIFIED for kernel-enforced resource limits and sandbox isolation.

## OpenClaw provenance and runtime

- `openclaw` executable was not found in PATH at capture time.
- No OpenClaw health response was observed on loopback port 18789 in the same audit window (HTTP status 000).
- Package-lock metadata under `/root/.openclaw/npm/projects/openclaw-codex-8902d781d4/` lists `@openclaw/codex` version `2026.9.8` and `@openai/codex` version `0.158.0`, with npm registry URLs and integrity metadata. This proves only that lockfile entries exist; it does not establish package authenticity, a complete Gateway installation, or runtime execution.
- The OpenClaw candidate remains NOT_VERIFIED. Do not execute the unverified wrapper, install packages, or start a Gateway until provenance and a controlled deployment plan are reviewed.

## Resource headroom

- Root filesystem reported approximately 39G total, 34G used, 5.3G available, 87% used.
- Memory reported 1.9Gi total, 597Mi available; swap 2.3Gi of 4.5Gi used.
- These values are a point-in-time snapshot, not a capacity guarantee. Avoid large scans/builds until disk and memory headroom are rechecked.

## Remediation proposals (not executed)

1. Define a non-root runner identity and explicitly set systemd hardening properties appropriate to runner requirements.
2. Establish explicit CPU, memory, and PID ceilings in the delegated cgroup and prove them with controlled resource-exhaustion tests.
3. Ensure the runner cannot access host secrets or modify protected host paths, and use ephemeral/isolated execution where feasible.
4. Verify OpenClaw package provenance, signature/checksum source, and gateway deployment method before installation or startup.
5. Re-run Q12 tests against the exact release-bound runner configuration and retain raw evidence.

## Gate decision

- Q12: NOT_VERIFIED — service active, but resource limits are unbounded in the inspected delegated cgroup and hardening properties are insufficient to prove isolation.
- OpenClaw: NOT_VERIFIED — executable and live Gateway health endpoint were not found; lockfile metadata is not runtime proof.
- Production: NO-GO.

This report is an unsigned audit note, not a security attestation.
