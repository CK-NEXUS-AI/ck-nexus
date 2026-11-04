# STEP 4 - Execution Host Preflight Status

Date: 2026-09-04

## Current status

`BLOCKED_BY_HOST_CONNECTIVITY`

## Servermall VM

- Service: #1061
- VM name: `10616a96dd5c121bb`
- Provisioning email confirms a public SSH endpoint exists.
- The public IP from the provisioning notice was probed on TCP/22 and returned `connection refused`.
- The corresponding Remote Desktop Commander device is currently `offline`.
- A support reply was sent under ticket `RSV-147847` requesting the current active public IP, SSH endpoint/port, VM power state, and SSH service state.
- No credential value is stored in this report.

## Q10 host decision

The Servermall VM is **not yet admitted as the Q10 execution host**.

Required before admission:
1. SSH connectivity succeeds.
2. Exact OS/CPU/RAM/storage are recorded.
3. user namespaces / unshare are tested.
4. bubblewrap is tested.
5. cgroups v2 is confirmed.
6. Docker/container runtime is confirmed.
7. audit logging is confirmed.
8. outbound network is confirmed.
9. frozen Q10 subject can be cloned and exact commit/tree verified.

## Tool installation correction

Python environment:
- Semgrep
- Bandit
- Ruff
- pip-audit

System/binary tooling:
- Trivy should be installed from its official package/binary distribution, not treated as a Python package.
- Docker should use the supported host installation path.
- Additional scanners must have version and checksum recorded in `host-setup.md` / `scan-manifest.json`.

## Self-hosted runner

The required self-hosted runner labels `[self-hosted, linux, q10-linux]` are `NOT_VERIFIED` at this stage.
GitHub-hosted `ubuntu-latest` successfully produced canonical export/validation evidence, but it is not substituted for the designated Q10 execution host.
