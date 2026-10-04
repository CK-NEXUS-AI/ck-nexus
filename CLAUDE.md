# CK-NEXUS Development Contract

CK-NEXUS is a governed AI control plane. This repository follows Evidence First and one canonical truth.

## Non-negotiable invariants

- GPT/LLM proposes; it is never the root authority.
- Policy Kernel decides allow/deny/approval.
- Execution Gateway executes only authorized actions.
- Verifier verifies outcomes independently where practical.
- Evidence Engine records reproducible proof.
- NO EVIDENCE -> NO DONE.
- DESIGN != IMPLEMENTATION != EXECUTION != VERIFICATION != PRODUCTION.
- RESEARCH != IMPLEMENTATION.
- REFERENCE != EVIDENCE.
- SHA MATCH != VERIFIED.
- LOCAL PASS != LIVE PASS.
- EXECUTED != VERIFIED.
- CODE != TEST != PRODUCTION.

## Canonical execution chain

Human Intent -> Agent Identity -> Lease -> Policy -> Approval -> Credential Reference -> Sandbox -> Execution -> Verification -> Evidence -> Memory -> Learning/Recovery

## Repository rules

1. Preserve existing production-readiness gates and evidence boundaries.
2. Do not weaken a gate merely to make CI green.
3. Never print or commit credentials, tokens, passwords, or private keys.
4. Prefer least privilege and fail-closed behavior.
5. Every material implementation claim must identify its evidence class.
6. Do not reuse stale evidence for a different source SHA/tree.
7. Changes affecting runtime/security must have tests and explicit verification criteria.

## Working method

Before changing code:
- identify the exact source/ref;
- inspect existing implementation;
- define acceptance criteria;
- make the smallest safe change.

After changing code:
- run applicable tests/checks;
- record exact command, result and artifact;
- distinguish execution from verification;
- never label production-ready without production evidence.
