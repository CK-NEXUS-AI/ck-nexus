# CK-NEXUS External Assessment Tracker X1

Status: ACTIVE / PRE-ASSESSMENT
Last updated: 2026-09-05

Purpose: track external security-assessment and certification intake without treating outreach, quotations, reports, or automated scans as certification or Q10 verification.

| Provider | Lane | Current status | Evidence received | Next action |
|---|---|---|---|---|
| Schellman | Compliance / certification / independent assessment routing | Detailed project intake sent; awaiting routing/next response | Human business-development reply received | Await technical/compliance routing and scoping response |
| Reconix | Secure code review / pentest / attestation | Technical RFI completed and sent for resource estimate / proposal | Reconix RFI template received and completed | Await receipt confirmation, proposal, quotation, and exact-subject support |
| Intertek | ISO/IEC 27001 / ISO/IEC 42001 certification | Application forms received; non-binding follow-up sent | ISO 42001 and ISO 27001 application forms | Prepare technical sections; obtain scope/quotation; keep consulting lane separate |
| Bureau Veritas | ISO/IEC 27001 / ISO/IEC 42001 certification | Application forms received; non-binding follow-up sent | ISO 27001 and ISO 42001 application forms | Prepare technical sections; await auditor guidance and proposal |
| NQA | Certification intake | Automatic acknowledgement only | Auto-acknowledgement | Await human response before further action |
| Aikido | Security tooling / scan evidence | Free-trial path confirmed; report export requires paid plan | Technical CLI/gating guidance received | Use free/trial evidence only; do not treat as independent attestation |
| HackerOne | Pentest / external security review | Intake previously submitted | Intake record only; no final report/attestation | Await human/provider confirmation |

## Authority rules

External-provider activity does not change production authority by itself.

Current authority remains:
- Q10 = NOT_VERIFIED
- Q11 = BLOCKED
- Q12 = BLOCKED
- Production = NO-GO / NOT CERTIFIED

Frozen Q10 subject:
- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

## Promotion criteria for an external result

An external result may be used as supporting evidence only when all applicable items are recorded:

- provider / assessor identity
- engagement scope
- exact subject or clearly defined environment
- methodology
- coverage
- findings
- severity
- remediation requirements
- retest result where applicable
- report/attestation/certificate identifier
- report date
- reviewer identity where available
- artifact/hash integrity where available
- independence/conflict-of-interest status
- limitations
- final decision state

No external result is allowed to silently overwrite a stricter CK-NEXUS fail-closed gate.
