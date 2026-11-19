# CK-NEXUS Blocker Substitution Matrix — 2026-09-04

Status: `RESEARCH / DEVELOPMENT_ONLY`

This document records safe alternatives for current CK-NEXUS blockers. It does not change release authority, Q10/Q11/Q12 state, Production state, or the frozen Q10 subject.

## Fixed authority state

- Q10 frozen commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Q10 frozen tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`
- Independent review: HUMAN only
- Owner final sign-off: HUMAN only

## Status vocabulary

- `SUBSTITUTED`: a safe replacement path has been executed successfully for the stated blocker.
- `CANDIDATE`: a credible replacement exists but needs exact-environment validation.
- `PARALLEL_RISK_REDUCTION`: useful evidence, but not a replacement for the authoritative gate.
- `NON_SUBSTITUTABLE_AUTHORITY`: replacing this gate would violate CK-NEXUS governance.
- `REMEDIATE`: fix or prove the concrete finding; do not bypass the gate.
- `WAIT_EXTERNAL`: external dependency cannot be safely bypassed.

## Matrix

| Blocker | Status | Replacement / strategy | Evidence / decision |
| --- | --- | --- | --- |
| OWASP Dependency-Check cold NVD database timeout | `SUBSTITUTED` | Use OWASP Dependency-Check's maintained NVD 2.0 data-feed mirror via `--nvdDatafeed` and keep scanner output isolated | Exact canonical main run `33799837854`; scanner `rc=0`; JSON report exists; 8 dependencies; 0 vulnerabilities; highest CVSS 0; artifact digest `sha256:bc28a9e0e594dc84a9e4f9fdb19dad9cfe0b812a6711b0b72670dad092963cc2` |
| Single dependency-vulnerability scanner dependency | `PARALLEL_RISK_REDUCTION` | Trivy + Grype + OWASP mirror + OSV offline cross-check | Trivy/Grype already pass on canonical main; OSV offline lane is being validated separately |
| Servermall SSH endpoint refusing TCP/22 | `CANDIDATE` | Do not block Q10 preparation on one VPS. Keep support ticket while qualifying an alternate proper Linux/WSL2 host | Servermall service claims active, but external probe still reached refusal before authentication. No credential workaround is appropriate |
| Android/proot cannot create required user namespaces | `WAIT_EXTERNAL` | Move native scan to a real Linux kernel environment; do not attempt userland/proot bypasses | Kernel namespace capability cannot be added by Python/package installation inside proot |
| Standard GitHub-hosted runner as native Q10 bwrap host | `REJECTED_FOR_NATIVE_Q10_HOST` | Use only for Development Docker/security lanes. Seek proper Linux VM or WSL2 host instead | Qualification run `33799692581`: cgroup v2 PASS and hardened Docker sandbox PASS, but `unshare` and `bwrap` failed with uid-map/permission errors; result `NOT_QUALIFIED`; artifact digest `sha256:b1a2d14ea46ef701965712e65f4906669c204446e29033c90bbdf60c43f65345` |
| No proper Linux host yet | `CANDIDATE` | WSL2 on a compatible Windows Server/VM is a high-priority alternative because current Codex Linux sandbox uses the normal bubblewrap path on WSL2; reuse existing Windows worker bootstrap rather than rebuild it | Existing branch `infra/windows-vps-worker-bootstrap-v1`; native Windows remains development-only. WSL2 must pass exact host qualification before use |
| Persistent self-hosted runner trust risk | `SUBSTITUTION_DESIGN` | If a self-hosted Q10 worker is used, register it as one-job ephemeral/JIT and wipe the environment after the job; preserve logs externally | GitHub recommends ephemeral self-hosted runners for autoscaling and warns about persistent runner compromise risk |
| Codex Security native deep scan blocked by ChatGPT/Codex usage quota | `NON_SUBSTITUTABLE_CANONICAL_GATE` | Wait for authorized quota reset, or use another officially authorized billing/auth path only with explicit human approval. Use other scanners only to reduce uncertainty in parallel | Semgrep/Trivy/Grype/Dependency-Check/OSV/Aikido cannot be promoted to native Codex Security evidence when the closure contract requires Codex Security |
| Codex worker requires bwrap split filesystem permission model | `NON_SUBSTITUTABLE_SECURITY_BOUNDARY` | Do not force a weaker sandbox merely to run. Current upstream allows legacy Landlock only when policy is sandbox-equivalent; split-only deny/read-only policy remains on bwrap | Current Codex Security worker extends read-only permissions, adds filesystem denies, and disables network. Upstream Codex keeps non-equivalent split policies on bubblewrap |
| 5 Semgrep ERROR-level findings on canonical main | `REMEDIATE_OR_PROVE` | Triage each finding using source-level proof and regression tests. Exact reviewed exceptions may be recorded only after proof; do not broad-suppress rules | Current candidates: tar extraction, verifier subprocess, runtime taint false-positive, two dynamic SQL placeholder findings |
| Tar extraction path traversal finding | `PROOF_CANDIDATE` | Existing code uses Python 3.12 `extractall(..., filter="data")`, then rejects symlinks. Add regression evidence for malicious absolute/parent/link entries before closing finding | Python 3.12 documents `filter="data"` as the hardened extraction filter but also recommends additional checks for untrusted archives |
| Dynamic verifier subprocess injection finding | `PROOF_CANDIDATE` | Verify command construction remains argv-only with no shell, allowlisted engine, digest-pinned trusted image, bounded resource settings and non-root identity; add attack regression around untrusted request fields | Existing `_verifier_container_command` validates engine/image/profile and returns an argv list; subprocess is called without `shell=True` |
| Runtime tainted-SQL Semgrep finding | `LIKELY_FALSE_POSITIVE_NEEDS_EXACT_PROOF` | Reproduce rule location against exact source and record why the taint path is not SQL if confirmed | Exact source around reported location builds an AI prompt from untrusted values, not a database query |
| Email Gateway dynamic SQL findings | `PROOF_CANDIDATE` | Keep values parameterized. Verify only the count-derived `?` placeholder string is interpolated and add SQL-injection regression tests for hostile IDs/worker values | Existing SQL interpolates only a comma-separated sequence of literal `?` placeholders; data values are supplied separately to sqlite execute |
| 10 Gitleaks historical Git-history findings | `REVIEW_HISTORY_NOT_CURRENT_TREE` | Current-tree scan remains separate. Review whether historical values were ever live credentials; rotate only affected credentials if needed. Do not rewrite history automatically | Current-tree secret scan is clean; findings originate from repository history |
| Exact-tree development evidence mismatch | `NON_SUBSTITUTABLE_EVIDENCE_BINDING` | Generate fresh evidence for the exact candidate tree or keep fail-closed. Never weaken comparison logic | A changed code tree correctly invalidates evidence bound to an earlier tree |
| Independent human review | `NON_SUBSTITUTABLE_AUTHORITY` | Prepare a deterministic review pack and reviewer checklist; a qualified human must review it | AI/tool review cannot satisfy independent-human authority |
| Owner final sign-off | `NON_SUBSTITUTABLE_AUTHORITY` | Prepare sign-off packet only; owner must make the final decision | Automation must stop before owner authority |
| Q11/Q12 blocked behind Q10 | `DEPENDENCY_BLOCK` | Prepare non-authoritative preflight work in parallel, but do not transition Q11/Q12 until Q10 closes | Prevents downstream status inflation |
| Knowledge semantic/vector retrieval uncertainty | `SUBSTITUTED_WITH_BASELINE_FIRST` | PostgreSQL lexical full-text retrieval baseline first; benchmark semantic/vector only after lexical results exist | Avoids adding Qdrant/vector infrastructure without measured benefit |
| Private-repo artifact provenance without GitHub Enterprise attestation | `CANDIDATE` | Continue exact commit/tree + workflow run + artifact SHA-256 + internal SHA256SUMS. Evaluate Sigstore/Cosign keyless only after privacy review because transparency logs may expose metadata | Provenance enhancement must not leak private repository metadata |
| Main branch currently unprotected/commit unsigned | `GOVERNANCE_CANDIDATE` | Prepare branch/ruleset hardening proposal and signed-commit policy; do not mutate repository governance settings automatically | Repository settings changes require explicit owner/governance authorization |

## Current alternative-host order

1. Proper Linux VM/VDS with unprivileged user namespaces, bubblewrap, cgroup v2 and Docker.
2. WSL2 on a compatible Windows Server/VM, only after native bwrap/userns/cgroup qualification inside WSL2.
3. One-job ephemeral/JIT self-hosted GitHub runner on either of the above for orchestration and reproducibility.
4. GitHub-hosted standard runners remain Development-only because native bwrap qualification failed.
5. Android/proot remains useful for control/preparation, not the native Q10 worker sandbox.

## Rules for trying alternatives

1. Search existing CK-NEXUS branches and upstream implementation before creating a new component.
2. Prefer a substitute that preserves or strengthens the original security boundary.
3. Reject alternatives that require disabling sandboxing, using danger-full-access, weakening exact-tree gates, exposing credentials, or changing human authority.
4. Execute safe alternatives against an exact subject and preserve raw output, tool version, digest, exit code and hashes.
5. A successful Development substitute does not automatically become canonical Q10 evidence.
6. Stop trying an already disproven path unless a material upstream/environment change occurs.

## Next experiments

- Finish OSV offline cross-check on exact canonical main.
- Create exact regression proof for the five Semgrep ERROR findings instead of suppressing them broadly.
- When any compatible Windows/Linux device becomes online, run WSL2/Linux host qualification before installing Codex Security.
- Keep Servermall support path open in parallel; do not wait on it exclusively.
- Before the Codex usage reset, finish all scan inputs, subject binding, artifact guards, Darker preparation and reviewer-pack generation so the authoritative native scan is a single controlled execution after reset.

## Non-negotiable conclusion

Some blockers have technical substitutes; authority gates do not. The correct objective is to replace unavailable infrastructure and unreliable tooling while preserving the closure contract—not to replace independent human review, owner sign-off, exact-subject evidence, or the required native Codex Security scan with weaker evidence.
