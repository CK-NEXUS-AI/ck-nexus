# CK-NEXUS Universal AI Operating Standard v2.0 — Draft

**Status:** DRAFT — NOT EFFECTIVE UNTIL OWNER SIGN-OFF AND POLICY IMPLEMENTATION
**Supersedes:** Proposed successor to `UNIVERSAL_AI_OPERATING_STANDARD_V1.md`; v1 remains unchanged and authoritative until adoption.
**Owner:** CK-NEXUS system owner
**Purpose:** Replace routine human-operated checking with governed, repeatable machine verification while retaining accountable human ownership for exceptional and high-impact decisions.

## 1. Governing principle

**Machines perform the work; independent controls prove the result; the owner governs the boundaries.** Human effort must not be required for routine checks that can be safely automated. Automation must never become self-authorizing.

Canonical chain:

`Human Intent → Agent Identity → Lease → Policy → Approval → Credential Reference → Sandbox → Execution → Verification → Evidence → Memory → Learning/Recovery`

This governance chain is canonical for CK-NEXUS. Capability and risk evaluation are policy checks within the chain, not replacements for approval, credential-reference, or memory controls.

## 2. Roles

- **Policy Kernel:** deterministic decision point; evaluates signed policy, identity, capability, scope, risk, quotas and lease. It is the only component allowed to authorize execution.
- **Execution Gateway:** runs only allowlisted operations in an isolated environment; no arbitrary shell or unrestricted credentials.
- **Verifier:** separate process or trust domain from the executor; reproduces checks and validates outputs against acceptance criteria.
- **Evidence Engine:** stores immutable, timestamped, content-hashed records and links each result to source SHA, tool versions, configuration, logs and verifier identity.
- **Certification Engine:** evaluates a versioned standard profile and creates a scoped, time-limited, digitally verifiable assessment statement only when all required gates pass.
- **Human Owner / Signer:** owns policy, signs policy releases and final owner declarations, approves exceptions and high-impact actions. Does not need to perform routine tests manually.

No agent may author, approve and independently verify the same high-risk change.

## 3. Automation levels and authority

| Risk | Examples | Default authority |
|---|---|---|
| L0 | Read-only inventory, status, static checks | Automatic within read scope |
| L1 | Isolated local build/test, temporary files | Automatic in sandbox with quota and cleanup rules |
| L2 | Reversible internal task or staging test | Automatic only under signed policy, lease, rollback and independent verification |
| L3 | Shared branch, shared data, service configuration | Automatic only for pre-approved, reversible allowlisted operations; otherwise owner approval |
| L4 | Credentials, security controls, external integrations, personal data, spending | Explicit owner approval before action; automated checks before and after |
| L5 | Production release, irreversible deletion, policy root changes, legal/financial commitments | Explicit owner approval and independent release gate; never self-approved by an agent |

A risk score cannot override a hard prohibition. Missing identity, scope, policy, lease, evidence or verifier means DENY.

## 4. Automated operating lifecycle

1. Receive intent and create immutable task ID.
2. Authenticate agent, tool, runtime and provenance.
3. Resolve exact capability and allowlisted target.
4. Evaluate policy and risk; record ALLOW / DENY / NEEDS_OWNER.
5. Issue short-lived, least-privilege lease with operation, target, limits and expiry.
6. Execute in isolated workspace; capture stdout/stderr, exit code, resource use and artifact hashes.
7. Run independent tests, security checks, reproducibility checks and post-condition checks.
8. Compare results with machine-readable acceptance criteria.
9. Append evidence and chain-of-custody metadata.
10. Derive status automatically; never let an agent type or promote its own status.
11. On failure, preserve state, classify cause, use only policy-approved alternatives, and stop repeated identical failures.

## 5. Status model

`DESIGNED → IMPLEMENTED → EXECUTED → VERIFIED → RELEASE_CANDIDATE → PRODUCTION`

Side states: `BLOCKED`, `FAILED`, `UNVERIFIED`, `EXPIRED`, `REVOKED`.

Status is computed from evidence. Execution is not verification. Passing CI is not deployment. A certificate is not proof outside its stated scope, commit, environment, profile and validity period.

## 6. Mandatory evidence for every automated decision

- Task and execution IDs; parent/delegation IDs.
- Agent, tool, verifier and runtime identities and versions.
- Repository, branch, exact commit SHA and dirty-tree state where applicable.
- Policy ID/version/hash; risk decision; lease scope and expiry.
- Inputs and configuration fingerprints; secrets must be represented only by safe references/hashes, never values.
- Commands/operations, start/end timestamps, exit codes and sanitized logs. Raw logs may exist only transiently in the isolated worker; redact secrets, credentials, personal data and sensitive identifiers before any persistence, evidence append, export or public exposure. Record the redaction method and result; if safe sanitization cannot be verified, do not persist or publish the log.
- Test names, results, coverage where required, security scan outputs and dependency/SBOM data.
- Artifact hashes, independent verifier result and evidence-chain reference.
- Final derived status, limitations, expiry and revocation state.

Evidence must be append-only or tamper-evident. Missing evidence blocks PASS and certificate issuance.

## 7. Independent verification requirements

- Executor and verifier must be logically separated; high-risk verification must use a separate identity or isolated runner.
- Compute the exact source/tree SHA before and after execution and compare for equality. Any mismatch means the source changed during assessment: mark the run BLOCKED/UNVERIFIED, discard its PASS result, and prohibit attestation until the complete assessment is rerun against one immutable subject.
- Verify lockfile integrity and installed dependency set.
- Run unit, integration, security, configuration, backup/restore and runtime health tests required by the selected profile.
- Verify negative cases: denied permissions, missing credentials, invalid signatures, expired leases, untrusted inputs and failed rollback.
- Re-run critical checks from recorded evidence where reproducibility is required.
- Record flaky, skipped, unsupported and unavailable tests explicitly; never count them as PASS.

## 8. Automated certificate model

The website may issue an immediate **CK-NEXUS Automated Conformance Attestation** when a complete assessment profile passes. Each attestation must bind to:

- Exact subject (repository/artifact/system), immutable SHA or artifact digest.
- Standard/profile and version, controls assessed, exclusions and test environment.
- Evidence manifest digest, verifier identity, issue time and expiry.
- Result, limitations, issuer key ID, signature and public verification URL/QR.
- Revocation status and superseding assessment, if any.

The attestation must clearly say it is a CK-NEXUS automated assessment, not an ISO certificate, legal certification, accreditation or third-party audit. External standards can be mapped to controls, but only an authorized/accredited certification body can issue the corresponding external certification.

## 9. Website workflow

`Register Subject → Select Profile → Verify Ownership/Scope → Run Assessment → Independent Verification → Generate Signed Attestation → Public Verify / Download Report`

The portal must provide a public verification page, machine-readable JSON, downloadable PDF, QR code, expiry and revocation lookup. It must never issue a passing result when mandatory checks are skipped, unavailable or unverifiable.

## 10. Owner signature and policy adoption

Policy adoption requires an explicit owner signature over the exact policy version and SHA-256 digest. The portal must show the digest, scope, consequences and pending status before signature. Required signer fields: full legal name, role, confirmation checkbox, signature input, timestamp and authentication evidence. A typed name alone is not represented as a legally binding signature unless the applicable e-signature requirements are separately met.

The signer does not need to approve routine test results individually. The signer approves the policy, profile, exceptions and high-impact actions defined above.

## 11. Rollout gates

- G0: Draft reviewed; no authority change.
- G1: Policy schema and decision tests implemented in a branch/sandbox.
- G2: Executor/verifier separation, evidence integrity and negative tests verified.
- G3: Portal issues only non-production test attestations; signature and revocation tested.
- G4: Independent security review and external legal/accreditation review where external claims are made.
- G5: Owner signs the exact policy digest AND an independent verifier confirms the adopted policy is enforced by the live Policy Kernel for the declared scope. Signature alone is insufficient; missing or failed enforcement evidence keeps v2 ineffective.
- G6: Production deployment separately approved and verified.

Until G5, v1 and existing hard safety boundaries remain in force. This draft does not authorize production deployment, destructive actions, permission changes, billing changes, repository pushes or merges.

## 12. Non-negotiable rules

- No evidence → no pass; no pass → no attestation.
- No access → no claim; no lease → no execution.
- No self-approval; no self-certification as an external accredited body.
- No arbitrary shell, unrestricted credentials or silent scope expansion.
- No hidden skipped tests or unreported limitations.
- No certificate without subject digest, profile version, verifier record, expiry and revocation path.
- Human oversight is reserved for ownership, policy changes, exceptions and high-impact decisions; routine checks are automated.
