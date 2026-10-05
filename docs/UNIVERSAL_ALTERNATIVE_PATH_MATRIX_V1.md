# Universal Alternative Path Matrix v1.0

Status: DESIGNED / DEVELOPMENT
Purpose: prevent deadlock without weakening evidence, authorization, security, or verification.

| Failure domain | Primary | Alternative A | Alternative B | Escalation | Evidence |
|---|---|---|---|---|---|
| Tool unavailable | native tool | equivalent authorized tool | alternate connector/runtime | capability owner | execution + result |
| API unavailable | provider API | approved provider | local/runtime fallback | provider owner | request/result + provenance |
| Quota exhausted | same provider | approved provider | local model | capacity owner | quota/error + alternate evidence |
| CI queued/stuck | hosted CI | diagnose/retry | approved alternate runner | CI owner | run/job/steps |
| Runtime unavailable | target runtime | isolated runtime | local/container runtime | runtime owner | environment + execution |
| Git write blocked | connector write | patch/artifact | authorized local git | repository owner | diff/tree/commit |
| Test environment broken | normal test env | isolated env | container/repro env | engineering owner | command/result/log |
| Web/source unavailable | source A | official alternate | independent source | research owner | source + timestamp |
| Credential failure | credential A | authorized credential B | non-secret alternative | security owner | reference + authorization |
| Deployment blocked | production | staging/candidate | isolated verification | release owner | release + verification |
| Browser failure | browser | API/tool | alternate browser/runtime | capability owner | action/result |
| Delegated agent unavailable | child agent | equivalent authorized child | parent execution | orchestrator | parent/child lineage |
| Evidence store unavailable | primary ledger | approved evidence store | immutable local bundle | evidence owner | hashes + provenance |
| Verifier unavailable | verifier A | independent verifier B | approved manual review | verifier owner | verifier + result |
| Data format failure | parser A | alternate parser | raw-preserving extraction | data owner | raw hash + normalized output |

## Rules
1. Alternatives must be pre-registered or policy-approved.
2. Never downgrade evidence requirements because the primary path failed.
3. Prefer the lowest-risk valid alternative.
4. Preserve the failed attempt; do not erase it.
5. Record alternative lineage, including parent execution where applicable.
6. Exhausted valid alternatives → BLOCKED or ESCALATE with evidence.
7. Never bypass identity, authorization, policy, high-risk approval, isolation, or required independent verification.
8. Alternative selection is itself auditable.