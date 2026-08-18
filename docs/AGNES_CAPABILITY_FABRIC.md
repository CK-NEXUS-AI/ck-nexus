# AGNES Capability Fabric — Post-P0

Status: `POST_P0 / SPEC+IMPLEMENTATION / NOT_PRODUCTION_EVIDENCE`

This package installs the CK-NEXUS contracts for the expanded AGNES capability
fabric while preserving fail-closed production governance.

## Installed capability domains

The catalogue covers cognitive governance, research, discovery, MCP, A2A,
REST/OpenAPI, durable workflow/event transport, agent/workload identity,
authorization, capability leases, sandbox selection, document/data intelligence,
multi-tier memory, vector/graph memory, RAM/PSI, ZRAM observation, CPU/GPU/NPU
routing, thermal/power, storage/IO, network adaptation, color/HDR, restoration,
resolution, visual verification, display profiles, evidence-quality receipts,
edge inference, bounded personalization, OpenTelemetry, evaluation, skill SBOM,
provenance, signing, privacy, economic routing, evidence graph, truthful claims,
digital-twin preview, shadow verification, dissent, adaptive autonomy, budget OS,
and bounded self-improvement.

## Installation semantics

"Installed" here means the module contracts and registry are present in the
CK-NEXUS source tree and importable by AGNES. External engines are intentionally
optional and are only **probed**, never auto-installed or auto-enabled.

`scripts/agnes_module_bootstrap.py` is plan-only. It has no package-install or
host-mutation mode. A future installer must be a separate governed workflow with
pinned versions, hashes, isolation, SBOM/license checks and explicit approval.

Examples of optional engines include Docling, DuckDB/Arrow, Qdrant/pgvector,
Neo4j, Temporal, NATS/Redis, OPA, Wasmtime, Docker, gVisor, Firecracker, FFmpeg,
VMAF, ONNX Runtime/ExecuTorch, OpenTelemetry SDK, Syft/Grype and Cosign.

This distinction is a security boundary:

- catalogue presence != external dependency installed
- dependency installed != authenticated
- authenticated != approved
- approved != write-authorized
- write-authorized != executed
- executed != verified
- local verification != staging or production verification

## Safe defaults

The capability catalogue is read-first. Critical bounded self-improvement is
`DISABLED` by default. Privilege-increasing skill transitions require ordered,
digest-bound evidence receipts; cryptographic signature and policy verification
remain external runtime responsibilities. Missing resource telemetry selects the
lowest-concurrency profile instead of assuming a healthy host. Read-only cgroup
detection records presence only and never claims delegated enforcement.

## Host rollout

A future operator workflow may consume `AGNESCapabilityFabric.external_dependency_plan()`
and propose selected optional engines for a specific Termux/VPS/container
profile. Installation must occur outside this fabric after policy review and must
record exact versions, package hashes, SBOM, license evidence, host identity and
test evidence.

Do not use this Post-P0 branch as Q10/Q11/Q12 evidence and do not merge it into
the frozen production-closure line while that closure remains active.
