# CK-NEXUS Blocker Register — 2026-10-01

| Blocker | Nature | Owner | Dependency | Reopen / Resolution Trigger |
|---|---|---|---|---|
| Q10 | Native Codex Security Deep Security Scan not executed | Release Authority / designated executor | Codex Security scan availability and exact frozen subject | Completed scan with scan ID, coverage, report SHA-256, completion timestamp |
| Q11 | Owner-authorized staging credential unavailable; prior run failed and sentinel absent | Release Authority | Secure secret mechanism + authorized staging credential | Credential configured and live sentinel evidence produced without exposing key |
| Q12 | Exact-subject delegated cgroup-v2 evidence not promoted | Release Authority / staging operator | Delegated cgroup-v2 runner | Successful exact-subject staging execution and bound evidence |
| Subject reconciliation | Branch/status/evidence lineage diverges | Release Authority | Explicit subject decision | Exact ref/source/tree/release/app subject reconciled |
| Independent verification | Final independent verification not closed | Independent reviewer | Reconciled subject + mandatory gate evidence | Independent reproduction and explicit reviewer verdict |

Production status remains NO-GO until mandatory evidence is closed and subject-consistent.