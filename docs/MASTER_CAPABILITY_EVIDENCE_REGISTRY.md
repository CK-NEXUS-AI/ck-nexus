# CK-NEXUS Master Capability & Evidence Reconciliation Registry v1

Status: **Development/Shadow — non-authoritative projection**

Baseline:
- repository: `spinlnw10-art/ck-nexus`
- main commit: `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
- main tree: `25d9c74db2b553667ad085172f8ac7beff4146aa`
- records: **52**
- records SHA-256: `75836acd700c7bd648bfb8c1503da61a80b15a2e825fd4b389b1f6191086e1e2`

## Purpose

This registry is a single reconciliation index across canonical implementation, Production gates,
development PR subjects, historical/chat-only reports, and research candidates. It prevents a
common CK-NEXUS failure mode: treating a feature name, a chat statement, a green CI run, or an
unmerged PR as stronger evidence than it actually is.

It **does not replace**:
- `creator_app/credentials/capability_registry.py` — runtime capability/credential/scope registry,
- `creator_app/agnes_ledger.py` — append-only evidence ledger,
- the Evidence / Verification planes,
- CK-NEXUS Governor,
- Production Q10/Q11/Q12 authority.

## Maturity model

| Level | Meaning |
|---|---|
| M0 | Missing |
| M1 | Candidate / research / prototype |
| M2 | Implemented partially or blocked measurement |
| M3 | Exact subject has successful measurement evidence; not independently verified |
| M4 | Independently verified exact subject |
| M5 | Explicitly adopted into canonical authority |
| M6 | Production-qualified exact subject with production-gate evidence |

The registry enforces: **CI success != VERIFIED**, **VERIFIED != Production GO**, and
**Development PR != canonical**.

## Current reconciliation highlights

- Production closure remains blocked by Q10, Q11 and Q12.
- PR #181 Expert Fabric is implemented but the current exact-head CK-NEXUS CI is failing while
  Security Attack Regression is successful; it is `M2_IMPLEMENTED_PARTIAL / BLOCKED_MEASUREMENT`.
- PR #182 capability research map remains research-only and its exact-head CK-NEXUS CI is failing.
- PRs #183-#188 have captured exact-head successful measurement evidence, but remain
  `M3_MEASURED / MEASURED_NOT_VERIFIED`, Draft/Open/Unmerged.
- Corrected AGNES Triad subjects (#168/#169/#174/#175/#177/#178/#179/#180) are tracked by their
  corrected/latest exact subjects rather than stale predecessor wording.
- Conversation-only Verifier Pro UI and Council runtime history are explicitly capped at M1 until
  repository/runtime evidence exists.
- OSV, Semgrep, Trivy, ZAP, Toxiproxy, gVisor, AuthZEN, A2A, Sigstore/SLSA and SPIFFE/SPIRE are
  research candidates here; the registry does not claim they are installed or verified.

## Files

`config/master_capability_evidence_registry.v1.json` is the registry index. It binds six record
fragments by SHA-256 and count. The combined canonical record sequence is separately sealed by
`records_digest_sha256`.

## Validation

```bash
python scripts/validate_master_capability_evidence_registry.py
pytest -q tests/test_master_capability_evidence_registry.py
```

The regression suite deliberately attempts forbidden promotions and requires rejection:
- measured M3 -> VERIFIED/M4 without independent-verifier evidence,
- Production qualification without canonical adoption and Production-gate evidence,
- chat-context promotion,
- duplicate IDs,
- unsealed record edits.

## Authority boundary

This registry is a **projection of evidence**, never a source of permission or truth escalation.
It cannot execute Q10/Q11/Q12, grant credentials, approve its own records, merge, deploy, or mutate
Production. Stronger status must originate from the appropriate CK-NEXUS authority and exact-subject
evidence.
