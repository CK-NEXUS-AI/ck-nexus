# CK-NEXUS Assurance Profile X1

Status: DEVELOPMENT BASELINE — NOT A CERTIFICATION
Last reviewed: 2026-09-05
Owner: CK-NEXUS
Scope: development, security assurance, AI governance, evidence, release verification

## 1. Purpose

CK-NEXUS Assurance Profile X1 defines a control and evidence baseline designed to prepare CK-NEXUS for independent assessment, due diligence, and future certification.

This profile is intentionally stricter than a simple "tests passed" model. It does not claim that CK-NEXUS is certified, compliant, or production-ready. External certification and independent assessment remain separate authority decisions.

## 2. Current authority state

- Q10: NOT_VERIFIED
- Q11: BLOCKED
- Q12: BLOCKED
- Production: NO-GO / NOT CERTIFIED

Frozen Q10 technical subject:
- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

No development change may silently redefine this frozen Q10 subject.

## 3. Two-layer assurance model

### Layer 1 — CK-NEXUS internal assurance controls

1. Fail-closed
   - Missing, stale, mismatched, or unverifiable evidence cannot produce a PASS/VERIFIED state.

2. Exact-subject verification
   - Security and release claims must identify the exact commit, tree, environment, and artifact set under review.

3. Evidence-first claims
   - Material claims require source, timestamp, subject, evidence location, integrity data, and verification state.

4. No self-approval
   - AI agents, automation, and system components cannot independently grant final VERIFIED, certification, or production approval to themselves.

5. Independent human review
   - Final independent security review must be performed by an authorized human reviewer who is independent from the automated execution path.

6. Owner sign-off
   - Final owner approval remains a separate human authority step after independent review.

7. Separation of duties
   - Execution, evidence generation, verification, independent review, and final approval are treated as distinct responsibilities.

8. Chain of custody
   - Evidence artifacts should be hashed, versioned, traceable, and protected from silent mutation.

9. Development/production separation
   - Development evidence cannot be promoted to production authority without explicit release gates and fresh evidence.

10. Truth-preserving UI and reporting
    - Inferred, stale, blocked, measured, and verified states must remain distinguishable.

## 4. External standards and guidance baseline

The profile is aligned at a high level with the following published frameworks and guidance. Exact certification conformity is determined only by the relevant accredited or independent assessor.

### Management systems

- ISO/IEC 27001:2022 — Information Security Management Systems
- ISO/IEC 27001:2022/Amd 1:2024 — Amendment 1
- ISO/IEC 42001:2023 — Artificial Intelligence Management System

### AI risk management

- ISO/IEC 23894:2023 — AI risk management guidance
- NIST AI RMF 1.0
- NIST AI 600-1 — Generative AI Profile

### Secure software development

- NIST SP 800-218 — SSDF Version 1.1 (final)
- NIST SP 800-218A — SSDF Community Profile for Generative AI and Dual-Use Foundation Models
- NIST SP 800-218 Rev. 1 / SSDF 1.2 — tracked as DRAFT only until finalized

### Application and agentic AI security

- OWASP GenAI/LLM security guidance
- OWASP Top 10 for Agentic Applications

## 5. CK-NEXUS extended controls

The following controls are intended to exceed a minimum checkbox posture by requiring technical proof and traceability.

### X1-01 Every Control -> Evidence

Every material control should map to:
- control objective
- implementation or policy
- exact subject
- automated or manual test
- observed result
- timestamp
- evidence artifact
- artifact hash
- reviewer
- decision state

### X1-02 Zero-Trust Agent Execution

Default posture for agents and tools:
- no implicit privilege
- least privilege
- explicit tool/capability authorization
- policy evaluation before sensitive execution
- high-risk operations require approval
- provider/tool output treated as untrusted input
- immutable authority boundary: agents cannot mark their own evidence VERIFIED

### X1-03 Exact-Subject Security Evidence

Security evidence should identify:
- repository
- branch/ref where relevant
- exact commit
- exact tree
- scanner/tool version
- scan configuration
- environment/runtime
- coverage
- findings
- exit/result state
- artifact hash

### X1-04 Software Supply Chain Assurance

Target evidence:
- SBOM
- dependency inventory
- vulnerability scan
- provenance
- pinned CI actions/tools where feasible
- artifact signing/verification
- third-party and provider inventory
- supplier risk record

### X1-05 AI System Inventory and Risk Register

For each material AI capability:
- system/component owner
- intended use
- model/provider
- data classes
- permissions/tools
- external dependencies
- known limitations
- failure modes
- security risks
- human oversight requirements
- monitoring
- rollback/disable path

### X1-06 Security Gate Before Canonical Adoption

Required sequence:
1. Search-first
2. Delta-only
3. Reuse/deduplicate
4. Benchmark/prove delta
5. Security review
6. Independent verification
7. Canonical adoption

No feature receives production authority solely because it is implemented or because CI passes.

### X1-07 Evidence Integrity and Chain of Custody

Evidence should support:
- deterministic manifest
- SHA-256 integrity
- append-only or hash-linked custody record where practical
- signature verification where applicable
- immutable frozen-subject references
- explicit distinction among system signature, independent human review, and owner sign-off

### X1-08 Recovery and Resilience Evidence

Target evidence:
- backup inventory
- restore test
- rollback test
- recovery objectives
- failure-mode test
- incident response process
- post-incident evidence preservation

## 6. Assessor-ready evidence package

The minimum assessor data package should be organized into:

1. Scope and organization
2. System architecture and data flows
3. Asset inventory
4. AI/model/provider inventory
5. Risk registers
6. Security policies and access model
7. Secure SDLC
8. Threat model
9. SBOM and supply-chain evidence
10. Test and security scan results
11. Vulnerability/remediation/retest records
12. Logging, monitoring, and incident response
13. Backup/recovery evidence
14. Evidence index and hashes
15. Independent reviewer decision
16. Owner sign-off

See `docs/assurance/ASSESSOR_DATA_ROOM_CHECKLIST_X1.md`.

## 7. Evidence maturity states

Use only these truth-preserving maturity labels:

- PLANNED
- IMPLEMENTED
- MEASURED_NOT_VERIFIED
- EXTERNALLY_REVIEWED
- VERIFIED
- BLOCKED
- NOT_APPLICABLE

Rules:
- IMPLEMENTED != VERIFIED
- CI_PASS != VERIFIED
- scanner success != certification
- signed artifact != independent human review
- external reviewer statement != owner sign-off
- missing evidence defaults to BLOCKED or NOT_VERIFIED, not PASS

## 8. Immediate development priorities

P0:
- resolve current Sonar Security Rating failures on active development PRs
- preserve exact-subject evidence for security findings
- complete assessor data-room inventory
- establish control-to-evidence index
- keep Q10 frozen subject unchanged

P1:
- formalize AI system inventory
- formalize supplier/provider inventory
- formalize risk register and treatment tracking
- complete SBOM/provenance/signing evidence
- exercise backup/restore and incident evidence flows

P2:
- map external assessor feedback to this profile
- close verified gaps through development PRs
- rerun security gates
- request independent review only against exact evidence

## 9. Non-claims

This document does NOT mean:
- CK-NEXUS is ISO/IEC 27001 certified
- CK-NEXUS is ISO/IEC 42001 certified
- Q10 has passed
- the product is production-ready
- any external auditor has accepted this profile

It is a preparation and assurance engineering baseline only.
