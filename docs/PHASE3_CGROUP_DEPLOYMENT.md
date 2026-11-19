# AGNES Phase3 — delegated cgroup v2 deployment

CK-NEXUS treats AGNES Phase3 kernel resource enforcement as a production gate, not a best-effort feature.

## Safe default

`docker-compose.prod.yml` defaults `CKNEXUS_AGNES_PHASE3_ENABLED=false` because ordinary Docker Compose does not guarantee that the non-root CK-NEXUS process owns a delegated writable cgroup v2 subtree with the `cpu`, `memory`, and `pids` controllers.

Do not set Phase3 to `true` merely because `/sys/fs/cgroup/cgroup.controllers` exists. The configured `CKNEXUS_AGNES_CGROUP_ROOT` must be a real delegation boundary that CK-NEXUS can manage as its non-root service identity.

## Required Q12 properties

The staging verifier must observe all of the following on the deployment class intended for Phase3:

- unified cgroup v2;
- delegated root writable by the CK-NEXUS non-root service identity;
- `cpu`, `memory`, and `pids` controllers available to the delegated subtree;
- creation of a child execution cgroup;
- `cpu.max = 20000 100000`;
- `memory.max = 67108864`;
- `pids.max = 16`;
- target child PID present in the child `cgroup.procs`.

Run `scripts/agnes_cgroup_v2_staging_gate.py` with:

```bash
CKNEXUS_ENVIRONMENT=staging \
CKNEXUS_AGNES_CGROUP_ROOT=/path/to/actual/delegated/cgroup \
python scripts/agnes_cgroup_v2_staging_gate.py
```

A `BLOCKED` or `FAIL` result keeps Phase3 disabled.

## Hosted-runner evidence

GitHub-hosted Ubuntu runners exposed cgroup v2 and the required controllers during Q12 investigation, but did not provide a delegation boundary from which the non-root runner could migrate/manage processes as required. That environment therefore does **not** satisfy Q12 and must not be used to claim Phase3 production readiness.

## Recommended production topology

Use a Linux service manager/orchestrator that explicitly delegates the required cgroup controllers to the CK-NEXUS service or to a dedicated worker service. A systemd deployment, for example, must use controller delegation (`Delegate=cpu memory pids`) and must verify the resulting service cgroup as the actual non-root CK-NEXUS identity before Phase3 is enabled.

The exact service-manager configuration is environment-specific. Q12 is PASS only after the supplied gate succeeds on the intended staging deployment class; documentation alone is not evidence.
