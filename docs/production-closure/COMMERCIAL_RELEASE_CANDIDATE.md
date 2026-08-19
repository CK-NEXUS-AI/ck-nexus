# CK-NEXUS Commercial Release Candidate Scope

Commercial classification: **Release Candidate Source Code**. Do not market this snapshot as Production Ready.

## Evidence-backed capabilities

The current frozen release line contains tested CK-NEXUS creator/runtime code, FastAPI application surfaces, agent orchestration, memory/storage paths, security controls, Docker packaging, live Redis/PostgreSQL idempotency evidence, observability alert delivery, dependency audit evidence, clean-machine candidate evidence, production-image candidate evidence and runtime license inventory.

Exact claims offered to a buyer must be limited to the committed code and evidence shipped with the package. Architecture diagrams, development-only `main`, AGNES research concepts, Cognitive Control Universe designs and integration plans are not production-runtime claims.

## Known release limitations

Production closure is currently blocked by three mandatory gates:

1. Q10 native Codex Security Deep Security Scan is not yet completed.
2. Q11 authorized live provider verification is blocked until an approved staging secret is configured and the exact verifier succeeds.
3. Q12 delegated cgroup v2 enforcement is blocked until the exact verifier succeeds on a non-root self-hosted Linux runner with a real delegated `cpu`, `memory`, and `pids` boundary.

Final Production Package has not produced a checksummed production artifact while those gates remain blocked.

## Permitted sales wording

- CK-NEXUS Release Candidate Source Code
- Includes evidence-backed tested components and release-closure tooling
- Production hardening/verification is in progress
- Buyer receives exact source/evidence scope identified in the release manifest

## Prohibited sales wording until closure completes

- Production Ready
- Fully production verified
- All security gates passed
- Deployment proven on every production environment
- Guaranteed autonomous operation

## Delivery scope for an RC sale

A delivery should include the exact source commit/manifest, dependency lock, Docker configuration, test suite, committed release evidence, third-party notices, operator runbook and a written list of unresolved Q10/Q11/Q12 gates. Any support, deployment service, provider credits, VPS, domain, third-party subscription or API usage should be priced separately unless explicitly included in the contract.

## Upgrade path to Production Ready

`Q10 native Deep Scan PASS -> Q11 live provider PASS -> Q12 delegated cgroup PASS -> provenance PASS -> Final Production Package SUCCESS -> checksum verification -> human release approval`.

No production claim is authorized before the full chain completes.
