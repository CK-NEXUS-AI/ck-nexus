# CK-NEXUS Evidence Registry Schema

Status: POST-P0 / DEVELOPMENT ONLY

Every persisted evidence record SHOULD contain the following minimum fields.

```json
{
  "schema_version": 1,
  "evidence_id": "EVD-...",
  "evidence_class": "PERSISTED_EVIDENCE",
  "gate": "Q10|Q11|Q12|P1|P2|NONE",
  "repository": "spinlnw10-art/ck-nexus",
  "source_commit": "<40-char SHA>",
  "source_tree": "<40-char tree SHA>",
  "subject_sha256": "<optional exact subject digest>",
  "run_id": "<provider run identity>",
  "artifact_id": "<provider artifact identity>",
  "artifact_sha256": "<sha256>",
  "started_at": "<RFC3339>",
  "completed_at": "<RFC3339>",
  "executor": "<bounded executor identity>",
  "verifier": "<independent verifier identity>",
  "result": "PASS|FAIL|BLOCKED|NOT_VERIFIED",
  "supersedes": [],
  "limitations": [],
  "production_eligible": false
}
```

## Invariants
- Raw API keys, passwords, cookies, private keys, bearer tokens, or authorization headers MUST NOT be stored.
- `TRANSIENT_EVIDENCE` cannot directly satisfy production gates.
- `PASS` must not be inferred from workflow success alone when the gate requires semantic evidence fields.
- Subject-changing remediation invalidates stale subject-bound production evidence.
- Evidence history is append-only; corrections use explicit `supersedes` references.
- A plugin/tool connection establishes at most CONNECTED/AUTHORIZED state, not EXECUTED or VERIFIED state.
- Production eligibility remains false until the canonical closure chain independently verifies Q10 -> Q11 -> Q12 -> provenance -> Final Production Package.

## External executor normalization
Each external service should be normalized into the same fields:
- GitHub Actions: workflow run ID, job ID, artifact ID, server-side digest.
- Codex Security: native scan ID, report digest, completion time, target/source binding.
- Linux/VPS executor: host identity digest, runner label, non-root identity, cgroup delegation evidence, command/result artifact digest.
- Vercel/Replit preview: deployment/run identity, immutable source commit, preview environment, test artifact digest; never production gate evidence by itself.
- Website readiness scanners: scan URL/result identity, timestamp, normalized findings, persisted report digest; classify as development/commercial evidence unless a canonical gate explicitly adopts it.
