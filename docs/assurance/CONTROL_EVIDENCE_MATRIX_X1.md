# CK-NEXUS Control-to-Evidence Matrix X1

Status: DEVELOPMENT / PRE-ASSESSMENT
Last reviewed: 2026-09-05

This matrix defines what evidence is required before a control may be treated as verified. It does not assert that the control is currently certified or externally accepted.

| ID | Control objective | Minimum evidence | Verification authority | Current truth state |
|---|---|---|---|---|
| X1-01 | Fail-closed release decisions | gate result, reason, subject, timestamp, evidence links | independent reviewer + owner for final release | MEASURED_NOT_VERIFIED |
| X1-02 | Exact-subject verification | commit, tree, environment, tool versions, artifact hashes | independent reviewer | MEASURED_NOT_VERIFIED |
| X1-03 | Evidence-first claims | claim record, source, observed_at, hash, freshness, status | evidence verifier | IMPLEMENTED / REQUIRES REVIEW |
| X1-04 | No self-approval | policy/control test showing agent cannot grant final VERIFIED | independent human | REQUIRES FORMAL PROOF |
| X1-05 | Independent human review | named reviewer, scope, decision, date, signed/traceable report | external/independent human | EXTERNAL_PENDING |
| X1-06 | Owner sign-off | owner decision bound to exact reviewed subject | owner human | BLOCKED_BY_PRIOR_GATES |
| X1-07 | Separation of duties | role matrix, permission test, audit evidence | independent reviewer | REQUIRES FORMAL PROOF |
| X1-08 | Chain of custody | manifest, hashes, custody links, signature verification | evidence verifier + human review | MEASURED_NOT_VERIFIED |
| X1-09 | Dev/production separation | environment definition, deployment policy, gate test | release reviewer | MEASURED_NOT_VERIFIED |
| X1-10 | Truth-preserving status | status schema, UI/API test, stale/inferred/verified differentiation | reviewer | REQUIRES FORMAL PROOF |
| X1-11 | Zero-trust agent execution | capability policy, deny-by-default tests, approval tests, audit logs | security reviewer | PLANNED / PARTIAL |
| X1-12 | Supply-chain assurance | SBOM, dependency scan, provenance, pinned CI, artifact signature | security reviewer | PARTIAL / NOT_VERIFIED |
| X1-13 | AI system inventory | inventory, owner, purpose, provider/model, data, permissions, risks | AI governance reviewer | PLANNED |
| X1-14 | AI risk management | AI risk register, treatment, residual risk, review record | AI governance reviewer | PLANNED |
| X1-15 | Secure SDLC | code-review policy, CI controls, SAST/dependency/secret/IaC results | security reviewer | PARTIAL / NOT_VERIFIED |
| X1-16 | Vulnerability remediation | finding, severity, owner, fix, retest, closure evidence | independent reviewer | PARTIAL / NOT_VERIFIED |
| X1-17 | Recovery/resilience | backup inventory, restore test, rollback test, recovery record | operations reviewer | PARTIAL / NOT_VERIFIED |
| X1-18 | Incident evidence preservation | incident process, log retention, evidence capture test | security/operations reviewer | PLANNED |
| X1-19 | External certification readiness | scope, policies, SoA/control mapping, audit evidence, corrective actions | certification body | EXTERNAL_PENDING |
| X1-20 | Production release authority | all required gates complete on exact subject | independent human + owner human | BLOCKED |

## Frozen Q10 authority

- Commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Q10: NOT_VERIFIED
- Q11: BLOCKED
- Q12: BLOCKED
- Production: NO-GO / NOT CERTIFIED

## Evidence record minimum schema

Each evidence item should contain at least:

```json
{
  "control_id": "X1-XX",
  "subject": {
    "commit": "...",
    "tree": "...",
    "artifact": "..."
  },
  "source": "...",
  "observed_at": "...",
  "tool_or_reviewer": "...",
  "result": "...",
  "evidence_uri": "...",
  "sha256": "...",
  "freshness": "...",
  "verification_state": "MEASURED_NOT_VERIFIED"
}
```

## Promotion rule

A control may move to VERIFIED only when:
1. the evidence is bound to the correct subject,
2. required evidence is complete,
3. integrity checks pass,
4. no blocking contradiction exists,
5. the required independent authority has reviewed it,
6. any required owner sign-off is complete.

Automation may collect and validate evidence, but may not self-grant final human authority.
