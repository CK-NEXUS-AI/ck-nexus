# CK-NEXUS Commercial Readiness Risk Register

Status: POST-P0 / DEVELOPMENT ONLY

| ID | Risk | Current state | Severity | Required closure evidence |
|---|---|---|---|---|
| R-001 | Q10 native deep security scan absent | OPEN | Critical | sealed scan ID, report SHA-256, completion time, exact frozen subject binding |
| R-002 | Q11 live provider credential path absent | OPEN | Critical | exact-subject live verifier run using approved secret path; no raw credential exposure |
| R-003 | Q12 delegated cgroup v2 enforcement absent | OPEN | Critical | non-root `cknexus-q12` runner, writable delegated cgroup, CPU/memory/pids enforcement evidence |
| R-004 | Final Production Package not produced | OPEN | Critical | reconciled provenance + checksummed final artifact |
| R-005 | Full exact source archives not yet independently materialized for both comparison bases | OPEN | High | exact commit archives + per-file SHA-256 + inventory + LOC |
| R-006 | Coverage baseline/gate incomplete | OPEN | High | reproducible coverage report and policy threshold |
| R-007 | Full E2E/performance/load/soak evidence incomplete | OPEN | High | exact-version measured reports with environment identity |
| R-008 | Commercial/IP legal package incomplete | OPEN | High | license terms, ownership dossier, notices, privacy/TOS/AUP, external legal review as applicable |
| R-009 | External plugins may return ephemeral/non-persisted results | CONTROLLED | High | classify transient results; persist only verified artifacts with digests |
| R-010 | Agent/tool over-privilege | CONTROLLED | Critical | least privilege, capability lease, expiry/revocation, approval gates, no-self-merge |
| R-011 | Post-P0 development could be mistaken for production evidence | CONTROLLED | Critical | explicit subject binding and DEVELOPMENT_ONLY labeling |
| R-012 | Paid resource creation or unexpected service cost | CONTROLLED | Medium | require known-free/sandbox scope or explicit cost authorization before creation |
| R-013 | Sales claims exceed verified capability | OPEN | High | claim-to-evidence traceability matrix and known-limitations disclosure |
| R-014 | Regulatory applicability uncertain by jurisdiction/use case | OPEN | High | EU AI Act / PDPA / GDPR applicability mapping and qualified legal review where required |

## Closure rule
A risk may move to CLOSED only when evidence is persisted, digest-addressed, source/run identities are known, and the independent verifier contract is satisfied. Chat claims, screenshots alone, or ephemeral MCP/plugin responses cannot close a production risk.
