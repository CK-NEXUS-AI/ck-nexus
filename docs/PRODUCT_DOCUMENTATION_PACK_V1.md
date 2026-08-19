# CK-NEXUS Product Documentation Pack V1

Classification: **SELLABLE SOURCE / PRODUCTION NO-GO** until Q10, Q11, Q12, provenance reconciliation, and the checksummed Final Production Package pass.

## 1. User Manual

CK-NEXUS is a governed cognitive operating layer. A user request flows through Access, the CK-NEXUS Cognitive Governor, Task Graph, AGNES/agents, replaceable model/tool workers, sandboxed execution, independent verification, and the Evidence Vault before a final result or governed mutation is accepted.

User-facing status must distinguish `VERIFIED`, `PASS_CANDIDATE`, `DESIGN_ONLY`, and `MISSING/BLOCKED`. UI labels must reflect runtime evidence and must never infer successful execution from a button click, model statement, or design mock.

Normal usage pattern: submit intent → inspect plan/capability request → approve only when policy requires → observe execution events → inspect verification/evidence → accept final result. High-risk actions require explicit governed capability and evidence.

## 2. Admin Guide

Nine mandatory invariants apply to administration:

1. Models/agents cannot authorize themselves.
2. Production mutations require traceable evidence.
3. Evidence is bound to exact commit/tree/runtime subject.
4. Raw credentials are isolated from agents and artifacts.
5. Capabilities are least-privilege and preferably leased/expiring.
6. Unknown or incomplete state fails closed.
7. Provider replacement cannot change CK-NEXUS authority.
8. Specialist agents/councils remain governed by the Cognitive Governor.
9. UI and status endpoints project runtime truth only.

Never edit a BLOCKED evidence file into PASS. Never use moving `main` as a production subject. If a frozen runtime path changes, rotate the subject and invalidate affected evidence.

## 3. API Documentation Contract

API surfaces should preserve these normalized concepts:

- Identity/Access: authenticated principal, tenant/workspace, session, permissions.
- Tasks: task ID, mission, state, Task Graph, correlation/causation IDs.
- Agents: governed role, capability lease, provider/model binding, budget.
- Tools/Connectors: discovery state, connection/auth state, capability schema, execution receipts.
- Verification: verifier identity, subject binding, policy decision, test result.
- Evidence: event ID, run ID, input/output digests, policy decision, timestamp, artifact fingerprint.
- Runtime overview: only observed values; absent telemetry must be `NOT_COLLECTED` rather than invented.

Mutation endpoints must be deny-by-default when no authoritative adapter/policy binding exists.

## 4. Security Whitepaper

### Threat model priorities

Primary threats include confused-deputy behavior, prompt/tool injection, credential exfiltration, capability escalation, untrusted connector/tool supply chain, sandbox escape, stale-evidence promotion, subject drift, provider failure, replay/idempotency failures, and UI status spoofing.

### Security architecture

CK-NEXUS separates intelligence from authority. Credentials are brokered/scoped rather than embedded in prompts or evidence. Capability grants are explicit. Untrusted tools/code are isolated. Independent verification is required before production acceptance. Evidence is content-addressed where possible and bound to exact runtime identity.

### Production security boundary

Dependency scans, Bandit, secret scanning, CI, and GPT simulations are useful supplementary checks but do not replace the mandatory native Codex Security Deep Security Scan. Live provider safety cannot be proven without a real authorized provider smoke. Process isolation cannot be proven without real non-root delegated cgroup v2 enforcement.

## 5. Deployment Guide

Development/staging and production evidence are separate. Deploy only from an exact reviewed release subject after all mandatory closure gates pass.

Required production-closure order:

`Q10 native deep security → Q11 live provider → Q12 delegated cgroup v2 → provenance reconciliation → checksummed Final Production Package → human review/merge decision`

A Q10 remediation that changes frozen runtime paths resets subject-bound closure from Q10. Q11 secrets belong only in authorized secret stores. Q12 must execute under a non-root delegated service identity on staging/self-hosted Linux.

## 6. Honest Sales Claims

Allowed current claims must be evidence-qualified. Architecture, UI concepts, capability catalogues, simulations, and Post-P0 AGNES work are not production verification. Buyer-facing material must identify known blockers and distinguish source-product readiness from production-deployment readiness.

Current release classification remains Production NO-GO. Historical/internal seller material has used an asking price around THB 149,000, but that is a seller-set commercial reference, not an independently validated market valuation. A defensible valuation should be revisited after Q10/Q11/Q12 closure, final package integrity, licensing/SBOM review, support terms, IP ownership review, and a buyer-acceptance test.

## 7. Development Direction

Post-P0 work should remain isolated from closure. Priority capability areas include governed research, memory/knowledge provenance, provider routing, MCP/A2A adapters, credential broker expansion, sandbox execution, verification mesh, evidence ledger, recovery/DR, observability/cost controls, and the Cognitive Control Universe runtime digital twin.
