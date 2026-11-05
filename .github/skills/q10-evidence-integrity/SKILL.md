---
name: q10-evidence-integrity
description: Use when preparing, validating, reviewing, or reporting CK-NEXUS Q10/Q11/Q12-Q16 evidence, scan results, manifests, attestations, or production gates.
---

# Q10 evidence integrity

1. Read the current canonical gate contract and subject manifest before running tools.
2. Record exact target commit SHA and tree SHA, source/runtime identity, tool/version, command, exit code, timestamps, output digests, and coverage.
3. Keep native-required scans distinct from substitute open-source scanners. Substitutes cannot silently satisfy a native-only contract.
4. Check report completeness, findings, coverage, attack paths, provenance, and exact subject match.
5. Never manufacture evidence, signatures, reviewer identity, scan IDs, timestamps, or PASS values.
6. Preserve frozen subjects and canonical evidence. Do not reset, check out, or commit on a frozen evidence subject, and never remove its security evidence. A legitimate dependency-lock change (including uv.lock) may be committed on a separate candidate branch only when the affected evidence is regenerated and re-baselined for the resulting exact subject; never treat old evidence as transferable.
7. Use status labels precisely: DESIGNED, IMPLEMENTED, EXECUTED, VERIFIED, PRODUCTION. NOT_VERIFIED and CLOSED-NOT-CERTIFIABLE are not PASS.
8. If a gate is blocked by paid tooling, unavailable credentials, or required human attestation, report the blocker and propose a transparent versioned alternative. Do not weaken the old gate in place.
9. Final report must state subject identity, evidence artifacts/digests, results, limitations, reviewer status, and production decision.
