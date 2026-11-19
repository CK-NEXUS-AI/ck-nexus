# CK-NEXUS Assessor Evidence Index X1

Status: DEVELOPMENT / PRE-ASSESSMENT
Last reviewed: 2026-09-05

Purpose: provide one navigation layer for external assessors and due-diligence reviewers while reusing existing repository evidence.

## Core assurance package

| Area | Primary evidence | Current state |
|---|---|---|
| Assurance baseline | `docs/assurance/CK_NEXUS_ASSURANCE_PROFILE_X1.md` | IMPLEMENTED |
| Control-to-evidence rules | `docs/assurance/CONTROL_EVIDENCE_MATRIX_X1.md` | IMPLEMENTED |
| Data-room checklist | `docs/assurance/ASSESSOR_DATA_ROOM_CHECKLIST_X1.md` | IMPLEMENTED |
| AI system inventory | `docs/assurance/AI_SYSTEM_INVENTORY_X1.md` | IMPLEMENTED / TO_VERIFY |
| Risk register | `docs/assurance/RISK_REGISTER_X1.md` | IMPLEMENTED / OPEN RISKS |
| Framework registry | `config/assurance/frameworks_x1.json` | IMPLEMENTED |

## Architecture and execution security

Reuse:
- `docs/CK_NEXUS_UNIFIED_ARCHITECTURE.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE1_SECURITY_BASELINE.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE1_VALIDATION.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE2_ISOLATED_SANDBOX.md`
- `docs/R24_COUNCIL_CAPABILITY_AUTHORITY.md`
- `docs/R28_UNIVERSAL_AUTO_CONNECTOR_FABRIC.md`
- `docs/CK-NEXUS-CANONICAL-MASTER-SOURCE-R9-R12.md`

## Secure development and scan evidence

Reuse / collect:
- `docs/SECURITY_AUDIT.md`
- GitHub Actions workflow definitions
- SonarQube/SonarCloud check results
- Semgrep results
- dependency vulnerability results
- secret scanning results
- IaC/container scan results
- test and coverage receipts

Do not mark this section complete until exact-subject result artifacts are archived with hashes.

## Q10 production-closure evidence

Frozen subject:
- commit `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- tree `0525195934f703a8becf8a39f6397b2411e0bb2e`

Required evidence:
- `scan-manifest.json`
- `findings.json`
- `coverage.json`
- sealed `report.md`
- native completion/seal receipt
- exact artifact SHA-256
- exact scan ID
- artifact guard
- fresh evidence-ledger/Darker verification
- exact tests/receipt
- machine finalizer
- evidence-signing verification
- independent HUMAN review
- owner HUMAN sign-off

Current state: INCOMPLETE / Q10 NOT_VERIFIED.

## External provider lane

Current preparation targets:
- Schellman
- Reconix
- Bureau Veritas
- Intertek
- NQA
- other independent assessors as applicable

For each provider retain:
- inquiry
- response
- scope
- reference/case ID
- NDA/ROE/SOW status
- exact-subject support
- deliverables
- reviewer independence
- timeline
- quotation
- final report/attestation/certificate if engagement occurs

## Evidence index rule

Every entry accepted into the final data room should be traceable by:
- evidence ID
- subject
- source
- observed_at
- file/artifact location
- SHA-256 where applicable
- tool/reviewer
- verification state
- supersedes/superseded_by relationship when newer evidence exists

Latest exact evidence wins.
