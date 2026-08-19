# Q12 Self-hosted Linux Delegation Setup

Status: provisioning guidance only; not Q12 evidence.

Q12 verification must run as a non-root GitHub Actions runner labeled `cknexus-q12`. Privileged host administration may be required once to provision the runner service and delegate a cgroup subtree, but the verification job itself must not use sudo/root to manufacture its test boundary.

## Required host properties

- Linux with unified cgroup v2 mounted at `/sys/fs/cgroup`.
- systemd capable of delegating controllers to the runner service.
- GitHub Actions self-hosted runner labels: `self-hosted`, `linux`, `cknexus-q12`.
- Runner service account is non-root.
- Delegated subtree exposes `cpu`, `memory`, and `pids`.

## Recommended systemd service design

Run the GitHub Actions runner under a dedicated non-root account (example `cknexus-runner`). In the service unit, use:

```ini
[Service]
User=cknexus-runner
Group=cknexus-runner
Delegate=cpu memory pids
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/actions-runner
```

Exact paths must match the installed runner. Do not copy the example blindly onto a host without checking its runner location.

After systemd reload/restart, identify the cgroup delegated to the runner service. Create or select a writable child boundary owned by the runner identity through the host's service provisioning mechanism. Set repository Actions variable `CKNEXUS_AGNES_CGROUP_ROOT` to that delegated child path. Never set it to `/sys/fs/cgroup`.

## Pre-verification checks as the runner identity

The following must succeed without sudo:

```bash
test "$(id -u)" -ne 0
test -n "${CKNEXUS_AGNES_CGROUP_ROOT:-}"
test "$CKNEXUS_AGNES_CGROUP_ROOT" != /sys/fs/cgroup
test -d "$CKNEXUS_AGNES_CGROUP_ROOT"
test -w "$CKNEXUS_AGNES_CGROUP_ROOT"
test -f "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.controllers"
for c in cpu memory pids; do grep -qw "$c" "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.controllers"; done
```

## Canonical verification

Only the existing `verify/q12-final-subject` workflow is release evidence. It checks out source `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`, verifies tree `0525195934f703a8becf8a39f6397b2411e0bb2e` and frozen subject `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`, then executes `scripts/agnes_cgroup_v2_staging_gate.py` as the non-root runner.

PASS requires observed `cpu.max`, `memory.max`, `pids.max` values and child PID attachment. A successful provisioning check alone is not Q12 PASS.
