# CK-NEXUS — Diligence Pack
Date: 2026-09-22

Evidence rule: Evidence → Claim.
Status ladder: TARGET → DESIGN → IMPLEMENT → TEST → VERIFIED.

| Layer | Status | Evidence Artifact | Gap |
|---|---|---|---|
| Identity | IMPLEMENT / TEST | R24 Council Capability Authority; identity tests | [ต้องตรวจสอบ] production identity deployment |
| Capability | IMPLEMENT / TEST | capability-policy schema; R24 authority/tests | [ต้องตรวจสอบ] live capability registry |
| Policy | IMPLEMENT / TEST | guardrails; policy schema; R24 | [ต้องตรวจสอบ] deployed-path enforcement |
| Budget | IMPLEMENT / TEST | SQLite transactional cost reservations; billing/tests | [ต้องตรวจสอบ] live distributed enforcement |
| Approval | IMPLEMENT / TEST | AGNES approval APIs; R24 | [ต้องตรวจสอบ] production approval path |
| Credential Reference | IMPLEMENT / TEST | CredentialBroker/Vault; R24 | [ต้องตรวจสอบ] live provider integration |
| Sandbox | IMPLEMENT / TEST | AGNES Phase 2/3 validation | production isolation/cgroup evidence incomplete |
| Execution | IMPLEMENT / TEST | AGNES execution controller/tests | [ต้องตรวจสอบ] live production execution |
| Verification | TEST | Phase 3 patch→test→scan→diff→evidence→candidate | [ต้องตรวจสอบ] commerce-deliverable verification |
| Evidence | IMPLEMENT / TEST | evidence registry; R9–R11 validation; audit/hash-chain | [ต้องตรวจสอบ] current end-to-end production chain |
| Recovery / Memory | IMPLEMENT / TEST | recovery/idempotency tooling and architecture | [ต้องตรวจสอบ] production recovery drill |

## Sale boundary

CK-NEXUS is an evidence-backed technical AI infrastructure asset / Safe Demo, not production-certified. Q10, Q11 and Q12 remain open.

Q10: dependency audit PASS but gate NOT_VERIFIED.
Q11: BLOCKED — live provider credential not configured.
Q12: BLOCKED — delegated cgroup v2 not available for required non-root identity.

## 3-line summary

1. READY TO SELL: evidence-backed architecture, implementation artifacts, tests, governance/evidence mechanisms and Safe Demo.
2. BEFORE PRODUCTION: Q10/Q11/Q12 plus current deployment, distributed runtime and end-to-end evidence.
3. LONG-TERM: agent-commerce rail adapters and verified settlement flows remain expansion targets until implemented and tested.
