# CK-NEXUS Standards Crosswalk X1

Status: DEVELOPMENT / PRE-ASSESSMENT
Last reviewed: 2026-09-05

## Purpose

This document maps CK-NEXUS assurance domains to major external standards and guidance at a **high level**.

It is not an official ISO conformity statement, certification decision, or clause-by-clause reproduction. Final clause/control applicability must be confirmed from licensed standards and by the selected assessor/certification body.

Current authority remains:
- Q10 = NOT_VERIFIED
- Q11 = BLOCKED
- Q12 = BLOCKED
- Production = NO-GO / NOT CERTIFIED

Frozen Q10 subject remains:
- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

## External baselines tracked

- ISO/IEC 27001:2022 + Amendment 1:2024
- ISO/IEC 42001:2023
- ISO/IEC 23894:2023
- NIST AI RMF 1.0
- NIST AI 600-1 Generative AI Profile
- NIST SP 800-218 SSDF 1.1
- NIST SP 800-218A
- OWASP Top 10 for Agentic Applications

NIST AI RMF 1.0 is the current published baseline used here; NIST has announced that the AI RMF is being revised, so CK-NEXUS should track the revision without treating draft material as final authority.

## High-level crosswalk

| CK-NEXUS assurance domain | ISO/IEC 27001 focus | ISO/IEC 42001 focus | ISO/IEC 23894 / NIST AI RMF | NIST SSDF | OWASP Agentic | CK-NEXUS evidence / control | Current state |
|---|---|---|---|---|---|---|---|
| Governance and scope | ISMS scope, leadership, governance | AIMS scope, AI governance | GOVERN / risk governance | Prepare Organization | governance / accountability | Assurance Profile X1, authority model | IMPLEMENTED / NOT_VERIFIED |
| Risk management | information-security risk | AI risk and opportunities | MAP / MEASURE / MANAGE | risk-informed SDLC | agent abuse scenarios | Risk Register X1 | IMPLEMENTED / OPEN RISKS |
| Asset and AI inventory | information assets | AI systems/resources | MAP context and inventory | software/component inventory | agent/tool inventory | AI System Inventory X1, asset checklist | PARTIAL |
| Roles and separation of duties | access and responsibility | AI oversight responsibilities | GOVERN accountability | secure-development roles | identity/privilege abuse | no self-approval, human review, owner sign-off | PARTIAL / NOT_VERIFIED |
| Access control and least privilege | identity/access controls | controlled AI access | GOVERN / MANAGE | Protect Software | identity & privilege abuse | capability policy, Credential Broker, Council Authority | IMPLEMENTED / NOT_VERIFIED |
| Agent/tool execution security | security operations | responsible AI operation | MANAGE AI operational risks | Protect Software | tool misuse, unexpected execution | AGNES executor boundary, sandbox, approval, kill switch | IMPLEMENTED / NOT_VERIFIED |
| Secure software development | secure change/development | AI lifecycle controls | lifecycle risk management | PO / PS / PW / RV practices | agentic supply-chain and code risks | CI, tests, SAST, dependency scans, exact-subject gates | PARTIAL / NOT_VERIFIED |
| Supply-chain assurance | supplier and technology controls | AI supplier/provider governance | third-party AI risks | provenance/dependency practices | agentic supply-chain vulnerabilities | SBOM target, provider inventory, pinned tooling | PARTIAL |
| Data / input / output trust | data protection | data for AI systems | GAI data and model risks | input validation and secure design | goal hijack / poisoned context | untrusted-input treatment, schema validation, redaction | PARTIAL |
| Provider/model governance | supplier management | model/provider lifecycle | MAP / MEASURE / MANAGE | third-party component governance | agentic supply chain | Provider Router, Credential Broker, AI inventory | PARTIAL |
| Logging and observability | event logging/monitoring | AI monitoring | MEASURE / MANAGE | vulnerability response evidence | anomalous agent behavior | observability, audit trail, evidence pipeline | IMPLEMENTED / NOT_VERIFIED |
| Vulnerability management | technical vulnerability management | AI system security risks | MANAGE | Respond to Vulnerabilities | exploit/tool misuse risks | Sonar, Semgrep, dependency/secret/IaC scans, retest target | PARTIAL / OPEN |
| Incident response | incident management | AI incident handling | MANAGE | vulnerability/incident response | agent compromise scenarios | incident-response evidence required in data room | PLANNED / PARTIAL |
| Resilience and recovery | continuity and recovery | operational continuity | MANAGE residual risk | recovery-aware practices | containment / rollback | backups, rollback, restore evidence target | PARTIAL / NOT_VERIFIED |
| Evidence integrity | records and auditability | AI accountability records | GOVERN / MEASURE evidence | secure-development records | forensic traceability | SHA-256, manifests, signing, chain of custody | MEASURED_NOT_VERIFIED |
| Exact-subject verification | change/release assurance | controlled AI system change | lifecycle measurement | provenance and verification | supply-chain integrity | frozen commit/tree, artifact hashes, scanner versions | MEASURED_NOT_VERIFIED |
| Human oversight | responsibility and approval | human oversight / accountability | GOVERN / MANAGE | review responsibilities | excessive autonomy mitigation | independent HUMAN review + owner HUMAN sign-off | EXTERNAL_PENDING |
| External assessment | independent assurance | AIMS certification readiness | external review of risk process | independent security review | independent testing | Schellman / Reconix / Intertek / Bureau Veritas lanes | EXTERNAL_PENDING |
| Production release authority | operational/release control | controlled AI deployment | risk acceptance and monitoring | release criteria | safe agent deployment | fail-closed Q10→Q11→Q12 sequence | BLOCKED |

## CK-NEXUS controls intended to be stricter than a minimum checkbox posture

### 1. Every Control -> Evidence
A policy statement alone is insufficient. Material controls should have technical or human evidence bound to a subject, timestamp, source, and verification state.

### 2. Exact-subject verification
Release/security evidence must identify the exact commit/tree and relevant artifacts rather than relying on a branch name or latest build.

### 3. No self-approval
AI/automation cannot grant itself final VERIFIED, certification, or production authority.

### 4. Independent human review + separate owner sign-off
Independent review and owner acceptance are different decisions and must remain distinguishable.

### 5. Fail-closed truth state
Missing, stale, conflicting, or mismatched evidence resolves to NOT_VERIFIED/BLOCKED rather than PASS.

### 6. Zero-trust agent execution
Agents and tools receive only explicit capabilities; high-risk actions require stronger authorization and policy checks.

### 7. Evidence chain of custody
Evidence should be hashed, versioned, traceable, and protected from silent mutation.

## Primary evidence already available in repository

- `docs/assurance/CK_NEXUS_ASSURANCE_PROFILE_X1.md`
- `docs/assurance/CONTROL_EVIDENCE_MATRIX_X1.md`
- `docs/assurance/AI_SYSTEM_INVENTORY_X1.md`
- `docs/assurance/RISK_REGISTER_X1.md`
- `docs/assurance/ASSESSOR_DATA_ROOM_CHECKLIST_X1.md`
- `docs/assurance/ASSESSOR_EVIDENCE_INDEX_X1.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE1_SECURITY_BASELINE.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE2_ISOLATED_SANDBOX.md`
- `docs/R24_COUNCIL_CAPABILITY_AUTHORITY.md`
- `docs/R28_UNIVERSAL_AUTO_CONNECTOR_FABRIC.md`
- `docs/PRODUCTION_CLOSURE_Q10_Q12_RUNBOOK.md`

## Priority gaps before assessor review

P0:
- complete exact-subject Q10 evidence
- resolve open security findings and retest
- create current SBOM/provenance evidence
- finalize access/role matrix
- produce runtime-confirmed AI/provider inventory
- exercise restore/rollback and incident evidence flow

P1:
- prepare ISO Statement-of-Applicability working draft with licensed-standard references
- complete supplier/provider register
- complete risk treatment owners and residual-risk decisions
- complete change/model-provider governance
- prepare assessor index with artifact hashes

## Public references

- ISO/IEC 27001: https://www.iso.org/standard/27001
- ISO/IEC 27001:2022/Amd 1:2024: https://www.iso.org/standard/88435.html
- ISO/IEC 42001: https://www.iso.org/standard/42001
- NIST AI RMF: https://doi.org/10.6028/NIST.AI.100-1
- NIST AI 600-1: https://doi.org/10.6028/NIST.AI.600-1
- NIST SP 800-218: https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP Agentic Top 10: https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/
