# CK-NEXUS Certification Portal — Product & Security Specification (Draft)

**Status:** DESIGN DRAFT — NOT DEPLOYED; NO CERTIFICATES ISSUED
**Target:** A web portal for immediate, evidence-backed CK-NEXUS automated conformance assessments.

## 1. Product promise

A system owner submits a repository, release artifact or service endpoint and selects a versioned assessment profile. The portal runs permitted checks, collects evidence, requests independent verification and immediately issues a digitally signed CK-NEXUS Automated Conformance Attestation when every mandatory gate passes.

The portal must not describe its own attestation as an ISO certificate, SOC 2 report, legal certification or accredited third-party certification. External certification requires the relevant authorized/accredited body and its audit process.

## 2. User journeys

1. **Register:** enter system name, owner, repository/artifact URL, immutable commit SHA or digest, environment and declared scope.
2. **Authorize:** prove ownership or permission to assess; select read-only or sandbox assessment. Never accept arbitrary shell commands from the browser.
3. **Select profile:** Core Integrity, Security Baseline, AI Governance, Operational Resilience, Release Readiness, or a mapped external-framework profile. These names must match the versioned profile catalog in Section 7.
4. **Assess:** execute version-pinned checks in isolated workers with quotas and no production credentials by default.
5. **Verify:** a separate verifier checks logs, signatures, artifact digests, policy results and required negative tests.
6. **Issue:** if all mandatory controls pass, create a signed attestation, PDF report, JSON record and QR/public verification URL.
7. **Sign owner declaration:** after the assessment, show the exact subject digest, profile, findings and attestation. Present an owner sign-off panel for the user's name, role and explicit signature/confirmation. Keep owner declaration separate from the machine-issued attestation.
8. **Maintain:** monitor expiry, reassess changed SHAs, publish revocations and preserve historical records.

## 3. Required pages

- Landing / explain what the portal certifies and what it does not.
- New assessment wizard.
- Live assessment progress and per-control results.
- Findings and remediation report.
- Certificate / attestation viewer.
- Public verification page by certificate ID or QR.
- Owner sign-off page with full name, role, exact digest, consent checkbox, signature capture and authenticated confirmation.
- Admin policy/profile management, key rotation and revocation dashboard.

## 4. Minimum attestation fields

`attestation_id`, `subject`, `subject_digest`, `scope`, `profile_id`, `profile_version`, `policy_digest`, `issued_at`, `expires_at`, `result`, `controls_passed`, `controls_failed`, `controls_skipped`, `limitations`, `evidence_manifest_digest`, `verifier_identity`, `issuer_key_id`, `signature`, `verification_url`, `revocation_status`.

A passing attestation is forbidden if any mandatory control is failed, skipped, unavailable or lacks evidence. Partial results must be labelled PARTIAL / NOT CERTIFIED.

## 5. Signing and trust

- Use a managed signing key (KMS/HSM preferred) inaccessible to assessment workers.
- Sign canonical JSON using a documented, interoperable signature format; publish issuer public keys and key IDs.
- Rotate keys with overlap and retain old public keys for historical verification.
- Separate machine attestation from the owner's declaration/signature.
- Record signer authentication method, consent text/version, timestamp, signed content digest and audit event.
- Do not claim that a typed name is legally binding without the applicable identity, consent, audit and legal requirements.

## 6. Security controls

- Strict SSRF protection, domain/IP allowlists, DNS rebinding defenses and blocked metadata/private ranges unless explicitly scoped for a controlled internal runner.
- No arbitrary command, script, URL fetch, package install or write operation from public requests. URL fetches and package installation are permitted only inside an isolated, quota-limited worker, after Policy Kernel authorization and strict domain/IP allowlist plus SSRF/DNS-rebinding checks; never execute them in the web/API process.
- Sandboxed ephemeral workers; no host mounts, privileged containers or shared writable workspaces.
- No production credentials by default; short-lived scoped credentials only when explicitly required and authorized.
- Rate limits, quotas, abuse detection, audit logging, tenant isolation and data retention controls.
- Immutable evidence storage, signed manifests, content hashes and independent verifier identity.
- Secrets redacted before logs are persisted; never place secrets in certificates or public verification pages.
- Signed policy/profile versions; two-person review for changes to issuer trust roots or certification rules.

## 7. Initial assessment profiles

- **Core Integrity:** source identity, lockfile, reproducible install, unit tests, runtime smoke, artifact digest.
- **Security Baseline:** dependency audit, secret scan, static analysis, authentication, authorization, secure defaults, negative tests.
- **AI Governance:** agent identity, capability boundaries, policy enforcement, leases, sandboxing, human/owner escalation, prompt-injection and tool-abuse tests.
- **Operational Resilience:** health/readiness, backup/restore, rollback, monitoring, resource limits, incident evidence.
- **Release Readiness:** exact SHA, clean/declared worktree, signed artifacts, CI evidence, independent reproduction, release provenance.

Each profile must have versioned machine-readable controls with mandatory/optional status, test method, evidence schema, severity and pass criteria.

## 8. Architecture

`Web UI → API/Auth → Assessment Orchestrator → Policy Kernel → Isolated Runner Pool → Evidence Store → Independent Verifier → Attestation Signer → Public Verification API`

The signer receives only a verifier-approved assessment manifest. The web/API layer cannot directly execute commands or sign arbitrary payloads. Public verification is read-only.

## 9. Initial delivery sequence

- P0: finalize policy v2 draft, control schema, threat model and claim wording.
- P1: local-only portal prototype with mock assessment results and a non-production signing key.
- P2: isolated assessment runner and evidence manifest; test negative cases.
- P3: independent verifier and signed test attestations; public verification page.
- P4: owner sign-off panel, expiry/revocation, PDF/JSON export and audit review.
- P5: independent penetration test and external accreditation/legal review before any external certification claim.
- P6: deploy behind authenticated access after explicit production approval.

## 10. Current boundary

This document is a design specification only. It does not claim the portal exists, that any certificate has been issued, that CK-NEXUS is production-ready, or that external standards have been achieved. No public port, DNS, TLS, billing or production service is changed by this draft.
