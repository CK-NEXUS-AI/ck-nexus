# CK-NEXUS Risk Register X1

Status: DEVELOPMENT / PRE-ASSESSMENT
Last reviewed: 2026-09-05

Scoring is intentionally qualitative until assessor-approved likelihood/impact methodology is finalized.

States:
- OPEN
- TREATMENT_IN_PROGRESS
- MEASURED_NOT_VERIFIED
- EXTERNAL_REVIEW_PENDING
- ACCEPTED_BY_HUMAN
- CLOSED_VERIFIED

| ID | Risk | Category | Current control/treatment | Evidence needed | State |
|---|---|---|---|---|---|
| RISK-001 | Automated system could overstate verification status | Governance | fail-closed states; no self-approval; authority separation | policy tests + independent review evidence | MEASURED_NOT_VERIFIED |
| RISK-002 | Evidence may not match the exact software subject | Integrity | frozen commit/tree + exact-subject verification | canonical manifest, hashes, scan receipt | TREATMENT_IN_PROGRESS |
| RISK-003 | Evidence artifact could be silently changed | Integrity | SHA-256, signing/chain-of-custody design | deterministic manifest + verification run + custody record | MEASURED_NOT_VERIFIED |
| RISK-004 | Agent/tool executes beyond intended privilege | Agentic security | capability registry, policy, risk classes, sandbox/approval gates | deny-by-default tests + privilege boundary tests | TREATMENT_IN_PROGRESS |
| RISK-005 | External tool/provider output is trusted incorrectly | Agentic security | treat external output as untrusted; policy boundary | input/output validation tests + threat model | OPEN |
| RISK-006 | Provider/credential leakage | Secrets | credential broker; no raw secret return; session controls | secret scan + credential-flow review + negative tests | MEASURED_NOT_VERIFIED |
| RISK-007 | Dependency/supply-chain compromise | Supply chain | dependency scanning, pinned actions in some workflows | SBOM + provenance + dependency policy + signature checks | TREATMENT_IN_PROGRESS |
| RISK-008 | CI passing creates false production confidence | Release governance | IMPLEMENTED != VERIFIED; production NO-GO until gates complete | release policy test + independent review | MEASURED_NOT_VERIFIED |
| RISK-009 | Security findings remain unresolved | Application security | Sonar/Semgrep/security scans + remediation process | exact finding list + fix + retest evidence | TREATMENT_IN_PROGRESS |
| RISK-010 | Branch/release governance insufficient | Repository governance | development PR workflow; no automatic production authority | branch/ruleset review + protected release policy evidence | OPEN |
| RISK-011 | AI provider/model changes without controlled re-evaluation | AI governance | provider router and policy concepts | model/provider change-control record + regression tests | OPEN |
| RISK-012 | Incomplete AI system inventory | AI governance | new AI inventory X1 | runtime-confirmed provider/model/data/tool inventory | TREATMENT_IN_PROGRESS |
| RISK-013 | Incomplete organizational risk/SoA evidence for ISO audit | Compliance readiness | Assurance Profile X1 + data-room checklist | management scope, SoA/control mapping, risk treatment plan | OPEN |
| RISK-014 | Incident response evidence is insufficient | Operations | monitoring/evidence concepts present | incident plan + tabletop/exercise evidence + preservation proof | OPEN |
| RISK-015 | Backup exists but recovery is not independently proven | Resilience | backup process/history | restore test + rollback test + RTO/RPO evidence | OPEN |
| RISK-016 | Remote execution/control plane may be unavailable | Operations | watchdog/service concepts | current transport health + recovery procedure + test | OPEN |
| RISK-017 | Third-party assessor scope may not bind to exact commit/tree | External assurance | explicit exact-subject request in provider intake | signed scope/proposal/report confirming subject binding | EXTERNAL_REVIEW_PENDING |
| RISK-018 | Certification provider consulting conflict may limit technical assessment | External assurance | separate certification and security-review lanes | provider scope confirmation | EXTERNAL_REVIEW_PENDING |
| RISK-019 | Q10 native security evidence incomplete | Production closure | Q10 fail-closed gate | required canonical scan artifacts + independent human review | OPEN |
| RISK-020 | Human approval identity/decision may be poorly bound to evidence | Governance | planned owner/reviewer sign-off | signed decision with exact subject and evidence hashes | OPEN |

## Immediate treatment priority

### P0
- RISK-002 exact-subject evidence
- RISK-004 agent/tool privilege
- RISK-007 supply chain
- RISK-009 unresolved security findings
- RISK-019 Q10 native evidence

### P1
- RISK-010 repository governance
- RISK-011 model/provider change management
- RISK-013 ISO audit evidence structure
- RISK-014 incident response
- RISK-015 recovery proof

### P2
- remaining maturity/documentation gaps

Risk closure requires evidence. A written mitigation statement alone is insufficient.
