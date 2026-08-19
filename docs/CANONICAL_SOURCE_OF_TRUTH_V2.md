# CK-NEXUS Canonical Source of Truth V2

## Authority precedence

1. Live GitHub repository/PR/workflow/artifact state.
2. Exact closure evidence bound to the frozen release subject.
3. Release artifacts and their server-side/content digests.
4. Historical chat, design notes, and prior reports.

Lower-precedence sources may explain history but may not override higher-precedence state.

## Current production authority

- Closure PR: #14, Draft/Open/Unmerged.
- Closure head: `a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53`.
- Runtime/security source: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`.
- Runtime/security source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`.
- Frozen runtime/deployment subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`.
- Production status: `NO-GO`.
- Q10: `NOT_VERIFIED`.
- Q11: `BLOCKED`.
- Q12: `BLOCKED`.
- Historical provenance: `8/8 PASS_CANDIDATE`, must be rerun after Q10/Q11/Q12 close.

## Development separation

`main` and Post-P0 branches may advance independently. Development success is not release evidence. New AGNES/Gen4 capabilities, Cognitive Control Universe UI, architecture contracts, sales material, or simulations must not be used to promote the frozen production subject.

## Evidence state machine

`DISCOVERED → CONNECTED → EXECUTED → VERIFIED → RELEASE_ELIGIBLE`

No state may be skipped. A claim may only use the highest state actually backed by evidence.

## Subject rotation

Any runtime-changing remediation creates a new candidate. The old subject remains historical, old subject-bound evidence becomes superseded, verifier branches/workflows are rebound, and closure restarts from Q10.

## External mutation boundary

Provider calls, deployment, destructive writes, merge, release tagging, credential changes, and other external side effects require governed capability/approval appropriate to risk. Model/agent output alone is never authority.

## Source inventory

Operational closure assets:

- `evidence/closure/CKNEXUS_CLOSURE_MANIFEST_V2.json`
- `evidence/q10/Q10_NATIVE_CODEX_SECURITY_REQUEST_V2.json`
- `evidence/q11/Q11_LIVE_PROVIDER_TEMPLATE_V2.json`
- `evidence/q12/Q12_CGROUP_V2_TEMPLATE_V2.json`
- `.github/release-tools/closure_master.py`
- `.github/workflows/closure-master-preflight-v2.yml`
- `docs/PRODUCTION_CLOSURE_MASTER_V2.md`
- `docs/FINAL_RELEASE_CHECKLIST_V2.md`
- `docs/PRODUCT_DOCUMENTATION_PACK_V1.md`
- `scripts/cknexus_gpt_parallel_contract_sim.py`

Post-P0 capability inventory:

- `backlog/CAPABILITY_SKILL_REGISTRY_V1.json`

## Promotion rule

Production Ready requires genuine Q10 + Q11 + Q12 PASS on the same exact subject, fresh provenance reconciliation, successful checksummed Final Production Package generation, and human release review. PR #14 must remain unmerged until then.
