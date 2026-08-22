# CK-NEXUS Q10/Q11/Q12 Executor Handoff

This document records the exact remaining production-closure work. It is a handoff/runbook only; it does not promote any gate.

## Current production state

- Production: NO-GO
- Q10: PREPARED_NOT_EXECUTED / NOT_VERIFIED
- Q11: BLOCKED until Q10 PASS
- Q12: BLOCKED until a qualifying Linux host is available

## Frozen production subject

- Repository: `spinlnw10-art/ck-nexus`
- Closure target SHA: `512837c8b1a3e6e8e844252a1b0781d8de011b07`
- Closure target tree: `43f9cb9691a0d028a1ef396a0a475c5cd80c4a99`
- Frozen runtime source SHA: `4cf17cd3befaafeaf64cd4c149739133aa220f73`
- Frozen runtime source tree: `dfe3888bb6adc9aebbb0351efe4a06006f4e0a48`
- Release subject manifest SHA-256: `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f`

## Q10 native Deep Security Scan

Q10 must be executed with the Codex Security native Deep Security Scan executor against the exact frozen subject above.

Required acceptance fields:

- `gate_result=PASS`
- `codex_security_deep_scan=PASS`
- `production_promotion_allowed=true`
- `codex_security_scan_id`
- `codex_security_report_sha256`
- `codex_security_completed_at`

Forbidden substitutions:

- Bandit-only scan
- Secret scan only
- Dependency audit only
- Manual review only
- Ordinary CI only

If Q10 finds a vulnerability that requires a code fix, the subject changes and previous subject-bound evidence must be invalidated/rebaselined before rerunning Q10.

## Q11 live provider smoke

Q11 must run only after Q10 PASS evidence is sealed. The prepared workflow is on branch `ops/q11-live-provider-smoke-v1`.

The workflow is intentionally fail-closed until Q10 shows:

- source SHA matches the frozen runtime source
- release subject manifest matches
- component result PASS
- gate result PASS
- native Codex Security deep scan PASS
- scan ID, report hash, and completion timestamp are present

Q11 also requires a brokered provider credential, such as a GitHub Actions `OPENAI_API_KEY` secret, without exposing the raw key.

## Q12 Linux sandbox evidence

Q12 cannot be completed on the current Windows VPS. A qualifying host must be Linux with real sandbox evidence including:

- cgroup v2
- delegated writable cgroup subtree
- CPU, memory, and PID controllers
- user/mount/PID/network namespaces
- no_new_privs / seccomp / capability drop path
- exact-subject evidence binding

The existing Linux preflight branch is `infra/q12-linux-host-preflight-v1`. A PASS_CANDIDATE from that preflight is not Q12 PASS; final Q12 requires exact production-subject sandbox enforcement evidence.

## Correct execution order

1. Freeze subject; do not merge/rebase production subject.
2. Run Q10 native Deep Security Scan.
3. If Q10 requires code changes: create a new subject and restart Q10.
4. If Q10 PASS: run Q11 live provider smoke.
5. Provision qualifying Linux host and run Q12 sandbox evidence.
6. Reconcile provenance.
7. Create checksummed final production package.

Until all steps pass with exact evidence, production remains NO-GO.
