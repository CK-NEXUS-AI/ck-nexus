# Q10–Q16 Evidence Closure Runbook

**Use:** Execution plan for authorized operators. This is not evidence that any gate has run or passed.  
**Default posture:** Read-only until the named system owner authorizes a specific live action.  
**Secrets:** Never paste API keys, tokens, credential files, or raw secret-bearing environment output into chat, issues, or reports.

## 1. Preflight — mandatory before any gate run

**Owner:** Release/evidence coordinator; verifier independently confirms.

1. Read the live GitHub main ref and target commit metadata. Confirm the candidate commit and tree are exactly the approved frozen values.
2. Verify commit signature and signer trust using the project's approved key policy.
3. Record UTC timestamp, repository/ref, commit, tree, manifest digest, tool versions, executor identity, and run ID.
4. Confirm a safe output directory with restricted permissions and enough disk space; never overwrite previous evidence.
5. Confirm required provider quota, billing, credentials, permissions, and runner capacity without printing secret values.
6. If any identity or precondition differs, stop, label the attempt BLOCKED, and ask the coordinator to re-freeze. Do not silently change target SHAs.

Suggested read-only checks (run in an approved shell with GitHub CLI authenticated to the intended account):

```bash
gh api repos/spinlnw10-art/ck-nexus/branches/main --jq '.commit.sha'
gh api repos/spinlnw10-art/ck-nexus/commits/cb612b72304246781b7dab48dad77d227c40d45d --jq '{sha:.sha, tree:.commit.tree.sha, verified:.commit.verification.verified, reason:.commit.verification.reason}'
```

These commands retrieve GitHub metadata only; their output must be captured as evidence and checked against the freeze table. They do not prove any Q-gate passed.

## 2. Gate execution matrix

| Gate | Accountable owner | Required access / preconditions | Required real evidence | Stop / acceptance rule |
|---|---|---|---|---|
| Q10 Native Codex Security | Security scan operator; independent security verifier | Approved OpenAI/Codex scan entitlement and billing/quota; read access to frozen source; restricted evidence storage | Native scan's complete output, exact source/tree, tool version, start/end UTC, exit code, findings summary, manifest digest, raw artifact digest, signature/verification record | Current reported attempt exited 2 with quota/billing error and 0/649 preflight. Do not substitute dependency scanners for the required native scan. No PASS until complete successful scan is independently verified |
| Q11 credentialed runtime smoke | Credential owner + runtime operator | Authorized secret-store/systemd credential reference; least-privilege host access; approved outbound provider access and sufficient quota | Unit definition, credential reference metadata (never value), service result, expected sentinel receipt, sanitized logs, exact source/tree, timestamps, artifact digest/signature | Missing credential/service or quota blocks the gate. No plaintext key in environment dumps, unit files, shell history, logs, or report |
| Q12 cgroup v2 enforcement | Runner/platform owner; kernel/runtime verifier | Approved self-hosted runner; non-root service account; delegated cgroup v2 subtree; permission to inspect kernel/cgroup state | Runner identity, service account and ownership, controllers available/enabled, cpu/memory/pids enforcement observations, limits and observed behavior, run ID, source/tree, raw logs and digest | Stop if runner is offline, service identity absent, cgroup root is wrong owner, or kernel enforcement cannot be observed. A config file alone is not proof |
| Q13 gate as defined in repository policy | Gate owner identified by current gate specification; independent verifier | Read current Q13 policy/spec and exact required test environment | Full Q13 result, test inputs/outputs, exact source/tree, run ID, raw artifact digest, verifier record | Historical PASS_CANDIDATE on `4cf17cd3…` is not candidate-bound. Do not guess the gate meaning if its current specification is missing |
| Q14 alerting / incident signal | Alerting service owner; observer independent of injector | Approved staging/test environment, written authorization for controlled failure injection, configured downstream alert destination | Injection authorization and correlation ID, actual downstream alert receipt/provider message ID, timestamps, delivery status, sanitized payload, source/config identity, artifact digest | No unauthorized production failure injection. A workflow pass or emitted local log is not a real alert receipt |
| Q15 gate as defined in repository policy | Gate owner identified by current gate specification; independent verifier | Read current Q15 policy/spec and exact required environment | Full Q15 result, inputs/outputs, source/tree, run ID, artifact digest, verification record | Historical PASS_CANDIDATE is not candidate-bound. Stop if acceptance criteria or test scope are unclear |
| Q16 image / license / release inventory | Build/release owner; supply-chain verifier | Access to exact built image and registry metadata; approved SBOM/license tools and policy | Immutable image digest, SBOM, license inventory and policy result, source/tree provenance, build/run ID, artifact digests, signature and verifier output | A tag or candidate label is insufficient. Verify exact image digest and its source lineage |

**Important:** This register intentionally assigns Q13 and Q15 to the owners defined by the current repository policy. Do not invent their technical meaning or run unreviewed procedures where the current specification cannot be located.

## 3. SonarCloud / PR check prerequisite

**Owner:** GitHub repository maintainer + SonarCloud project administrator.

Reported PRs #289, #290, and #291 have SonarCloud checks cancelled/failed, with a 404/project-access issue reported. A cancelled check is not success.

1. Inspect the exact PR head SHA and check-run details.
2. Confirm the SonarCloud project key, organization binding, app installation/permissions, and pull-request analysis configuration.
3. If project access is missing, have an authorized project administrator repair the mapping. Do not bypass a required check by editing branch protection without an approved policy change.
4. Re-run analysis on the exact PR head and capture a successful check-run URL and timestamp.
5. If SonarCloud is formally replaced, document the replacement control, equivalence rationale, owner, and approval in a separate governance decision.

## 4. Execution record template

For each gate, create a new immutable record:

```yaml
evidence_id: "<new unique ID>"
gate: "Q10"
status: "BLOCKED | EXECUTED | VERIFIED | NOT_VERIFIED"
target:
  repository: "spinlnw10-art/ck-nexus"
  ref: "main"
  commit: "<full SHA>"
  tree: "<full tree SHA>"
executor:
  identity: "<approved non-secret identity>"
  run_id: "<provider run ID>"
  tool_version: "<exact version>"
timing:
  started_at_utc: "<ISO-8601>"
  finished_at_utc: "<ISO-8601 or null>"
result:
  exit_code: null
  summary: "<factual short summary>"
artifacts:
  - uri: "<restricted immutable artifact location>"
    sha256: "<digest of the actual artifact>"
    signature_key_id: "<key ID or null>"
    signature_verified: false
verification:
  verifier_identity: "<separate reviewer identity or null>"
  decision: "PENDING"
  reviewed_at_utc: null
limitations:
  - "<quota, access, missing receipt, or other limitation>"
```

This is a schema template, not a filled result. Replace every placeholder only with observed values. Do not record `VERIFIED` until the verification actually occurs.

## 5. Closure sequence

1. Freeze and independently verify candidate identity.
2. Repair authorized prerequisites (quota, credential reference, runner identity/cgroup delegation, alert destination, SonarCloud access).
3. Execute each gate separately; preserve failures and retries as distinct artifacts.
4. Run independent evidence-integrity checks and confirm every artifact's source/tree binding.
5. Update the evidence register with immutable links and actual statuses.
6. Independent reviewer signs ACCEPT or REJECT with reasons.
7. Only after all required release gates and approvals pass may a separate release decision be considered. This runbook itself never authorizes merge, deployment, or production promotion.
