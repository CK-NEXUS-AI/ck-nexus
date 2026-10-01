# CK-NEXUS Gate Status Snapshot — 2026-10-01

| Gate | Status | Evidence qualification |
|---|---|---|
| Q05 | PASS* | Subject-bound; PASS only for its evidenced subject |
| Q08 | PASS* | Subject-bound; PASS only for its evidenced subject |
| Q09 | PASS_CANDIDATE | Subject-bound |
| Q10 dependency | PASS component | pip-audit 0 vulnerabilities; does not close whole Q10 |
| Q10 whole | NOT_VERIFIED | Native Codex Security Deep Security Scan not executed |
| Q11 | BLOCKED | Credential not configured; prior run 31950795711 failed; sentinel absent |
| Q12 | NOT PROMOTED | Run 35421281024 succeeded but evidence is bound to old subject 96dcd0... |
| Q13 | PASS_CANDIDATE | Old-subject evidence |
| Q14 | PASS* | Old-subject evidence |
| Q15 | PASS_CANDIDATE | Old-subject evidence |
| Q16 image | PASS_CANDIDATE | Old-subject evidence |
| Q16 licenses | PASS | Old-subject evidence |
| Independent verification | NOT CLOSED | Subject reconciliation remains unresolved |
| Production | NO-GO | Mandatory evidence unresolved |

Canonical disposition: no gate is promoted to production authorization by this snapshot.