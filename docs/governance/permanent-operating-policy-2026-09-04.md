# CK-NEXUS Permanent Operating Policy

Status: DEVELOPMENT GOVERNANCE CANDIDATE
Date: 2026-09-04

This policy is intended to make critical CK-NEXUS operating rules durable in the repository rather than dependent on chat memory.

## 1. Canonical truth and evidence

- Latest exact evidence wins.
- Development evidence is not Production evidence.
- A capability name, config entry, design document, chat claim, or AI statement does not prove implementation or verification.
- Exact commit SHA and tree SHA must be recorded before evidence-producing scans.
- Frozen Q10 subject must not be modified.
- Q10 remains NOT_VERIFIED until all required canonical evidence, independent HUMAN review, and Owner HUMAN sign-off are complete.
- Q11 and Q12 remain BLOCKED until their prerequisites are satisfied.
- Production remains NO-GO / NOT CERTIFIED until governance explicitly transitions it.

## 2. Search-first and reuse

Before creating or importing a capability:

SEARCH_FIRST -> DELTA_ONLY -> REUSE/DEDUP -> BENCHMARK -> SECURITY_REVIEW -> INDEPENDENT_VERIFICATION -> CANONICAL_ADOPTION

Do not duplicate existing runtime, evidence, memory, orchestration, provider, connector, or governance capability without proving a meaningful delta.

## 3. Docker helper farm default

When a task can be accelerated safely with containers, use a Docker helper farm by default in the Development/Security preflight lane.

Preferred helpers include, where relevant:

- Semgrep
- Trivy
- Gitleaks
- Checkov
- ShellCheck
- Hadolint
- OWASP Dependency-Check
- Syft / CycloneDX for SBOM
- Grype for vulnerability cross-check
- Cosign for image/evidence integrity
- OWASP ZAP for DAST when a safe runtime target exists

For every helper execution:

1. Verify the exact source commit and tree first.
2. Mount source read-only where practical.
3. Record tool version.
4. Record container image digest when containerized.
5. Record command/scope.
6. Record exit code.
7. Preserve raw output/artifact even when findings are present.
8. Do not let scanner non-zero exit codes destroy evidence capture.
9. Redact secrets from user-visible evidence.
10. Keep Development Security Evidence separate from Q10 Canonical Evidence.

## 4. Fail-closed rules

- Missing evidence means not verified.
- Unknown state remains UNKNOWN/BLOCKED as appropriate.
- Do not fabricate artifacts, findings, coverage, hashes, attestations, signatures, reviews, or scan completion.
- Do not weaken exact-tree, evidence, approval, or security gates merely to make CI pass.
- Do not run auto-fix commands such as `ruff check . --fix` on an exact verification subject.

## 5. Separation of duties

AI and automation may perform safe, reversible development, analysis, scanning, evidence preparation, and remediation proposals.

AI and automation must not:

- self-approve
- act as independent reviewer
- create owner sign-off
- merge or deploy Production without required human authority
- approve paid actions
- expose or persist raw credentials
- bypass credential, policy, security, or evidence gates

Independent reviewer: HUMAN.
Owner final sign-off: HUMAN.

## 6. Recovery vs Development

Recovery reconstructs and verifies historical/canonical state. Development creates new state.

Do not create new features while claiming to perform recovery.

Historical and recovery material must be classified before adoption, for example:

- VERIFIED_HISTORICAL
- SUPERSEDED
- RECOVERY_CANDIDATE
- DESIGN_CANDIDATE
- DUPLICATE
- HISTORICAL_CLAIM
- UNVERIFIED_CLAIM
- RECONCILIATION_REQUIRED

Canonical source wins mapped conflicts unless an explicit reviewed migration adopts a measured delta.

## 7. Persistent configuration boundary

Repository policy/configuration is the durable source for operating rules. Chat memory is supplemental only.

`SYSTEM_MANIFEST.yaml` may define declarative desired configuration, but it must not be allowed to assert live runtime health, connectivity, VERIFIED status, Production readiness, or certification without backend/evidence authority.

Recommended truth layers:

1. Declarative configuration truth
2. Authoritative runtime truth
3. Verification/evidence truth

UI is projection only and must not invent state.

## 8. Learning and self-healing

Allowed automatically for reversible operations:

- collect logs/metrics
- reflection
- generate proposals
- restart bounded reversible components
- restore from verified checkpoint
- quarantine faulty components

Not allowed automatically:

- modify protected source and self-approve it
- auto-merge
- auto-deploy Production
- change governance/security policy without authorization
- convert proposals directly into VERIFIED capability

## 9. Credential handling

- Never place passwords, API keys, private keys, OTPs, tokens, session cookies, or long-lived credentials in evidence or chat output.
- Provisioning credentials should be rotated after first successful administrative access.
- Evidence should contain only variable names, secret references, or `[REDACTED_SECRET]` placeholders.

## 10. Current immutable governance baseline

Frozen Q10 subject:

- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

Current status until exact evidence changes it:

- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

This file records operating policy only. It is not independent verification, Owner sign-off, certification, or Production authorization.
