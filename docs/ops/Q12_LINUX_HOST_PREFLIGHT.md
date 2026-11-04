# Q12 Linux Host Preflight

This check is intentionally fail-closed and read-only. It verifies whether a Linux host is a plausible candidate for CK-NEXUS Q12 execution evidence.

It checks:

- systemd availability
- cgroup v2 mount
- `cpu`, `memory`, and `pids` controllers
- user, mount, PID, and network namespace creation
- `no_new_privs` support
- writable cgroup subtree delegation at the current boundary

A `PASS_CANDIDATE` result is not Q12 PASS. Authoritative Q12 still requires the exact production subject, bounded CPU/memory/PID enforcement, filesystem/network isolation, escape attempts, fail-closed behavior, timestamps, digests, and evidence reconciliation.

Termux/Android and Windows Server are not authoritative substitutes for this Linux contract.
