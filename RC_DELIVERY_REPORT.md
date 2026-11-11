# CK-NEXUS Release Candidate — Delivery Report

**Report date:** 2026-11-11
**Decision:** Owner-approved Plan A — RC with SHA-bound Disclosure
**Base commit before disclosure:** f8c8b08d1f456d38d6ff30b9f1f2ebb0456ff6b6
**RC artifact baseline:** 8ac1ca7f9cb649ff230767dbf26167dc5bc7812c
**RC branch:** fix/pr365-office-archive-hardening-20261111
**This correction:** Documentation-only update to README.md and this report. The immutable commit SHA for this correction is established by Git after commit.

---

## 1. Critical Disclosure

No Q10–Q16 gate evidence is bound to the RC artifact baseline 8ac1ca7f9cb649ff230767dbf26167dc5bc7812c. All evidence listed below belongs to prior candidate subjects. No gate was re-run or re-verified during this documentation correction.

This RC is for technical evaluation and due diligence. It is NOT Production Ready and NOT Certified 100%.

## 2. Verified Evidence Provenance

The following values were read directly from the evidence files in this worktree. Q10 uses the Release subject field in its Markdown attestation; Q11–Q16 use the source_sha field in each JSON file.

| Gate | Evidence file | Actual source subject | Status / limitation |
|---|---|---|---|
| Q10 Security Review | evidence/Q10_REVIEW_ATTESTATION.md | a31f82d1d45c3398ae14fb506d0893f67a55234d | Owner attestation only; scanner report NOT_VERIFIED; independent review outstanding |
| Q11 Live Provider | evidence/Q11_OPENAI_LIVE.json | a31f82d1d45c3398ae14fb506d0893f67a55234d | PENDING / BLOCKED; live-provider verification incomplete |
| Q12 Delegated cgroup v2 | evidence/Q12_CGROUP_V2.json | 512837c8b1a3e6e8e844252a1b0781d8de011b07 | Prior-candidate evidence; buyer must re-verify |
| Q13 PostgreSQL DR | evidence/Q13_POSTGRES_DR.json | 4cf17cd3befaafeaf64cd4c149739133aa220f73 | Prior-candidate evidence; buyer must re-verify |
| Q14 Observability | evidence/Q14_OBSERVABILITY_ALERT.json | 4cf17cd3befaafeaf64cd4c149739133aa220f73 | Prior-candidate evidence; buyer must re-verify |
| Q15 Clean Machine | evidence/Q15_CLEAN_MACHINE.json | 4cf17cd3befaafeaf64cd4c149739133aa220f73 | Prior-candidate evidence; buyer must re-verify |
| Q16 Production Image | evidence/Q16_PRODUCTION_IMAGE.json | 4cf17cd3befaafeaf64cd4c149739133aa220f73 | Prior-candidate evidence; buyer must re-verify |
| Q16 Runtime Licenses | evidence/Q16_RUNTIME_LICENSE_SUMMARY.json | 4cf17cd3befaafeaf64cd4c149739133aa220f73 | Prior-candidate evidence; buyer must re-verify |

No Q10–Q16 evidence file was modified by this correction.

## 3. CI Evidence

GitHub check runs were confirmed on the RC artifact baseline 8ac1ca7f9cb649ff230767dbf26167dc5bc7812c:

- test: SUCCESS — https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42928860524
- attack-regression: SUCCESS — https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42928860527
- preflight: SUCCESS — https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42928860601

These checks apply to 8ac1ca7f only. They do not automatically apply to this subsequent documentation correction commit. Any new CI triggered by pushing this correction must be checked against its exact resulting SHA.

CI pass is not Q10–Q16 gate closure.

## 4. Buyer Verification Obligations

Before production deployment, the buyer must:

1. Obtain an independent Q10 security review and owner approval against the exact purchased commit.
2. Complete Q11 live-provider verification using a buyer-controlled funded provider credential stored only in an approved secret store.
3. Re-verify Q12–Q16 against the exact purchased commit and preserve each evidence artifact, subject SHA, tree, manifest, and run reference.
4. Verify CI and dependency/security checks on the exact purchased commit.
5. Review the Q10–Q16 Closure Contract, Release Checklist, Seller Checklist, and all disclosed limitations.

## 5. Honest Assessment

This RC provides a source-code candidate and preserved implementation/evidence history for technical evaluation. The available records do not establish independent security review, successful live-provider verification, or complete exact-subject Q10–Q16 evidence for the RC artifact baseline.

No market valuation, resale percentage, or guaranteed sale price is asserted.

## 6. Disclosure Documents

- evidence/Q10_REVIEW_ATTESTATION.md
- evidence/Q11_OPENAI_LIVE.json
- evidence/Q12_CGROUP_V2.json
- evidence/Q13_POSTGRES_DR.json
- evidence/Q14_OBSERVABILITY_ALERT.json
- evidence/Q15_CLEAN_MACHINE.json
- evidence/Q16_PRODUCTION_IMAGE.json
- evidence/Q16_RUNTIME_LICENSE_SUMMARY.json
- docs/Q10_Q16_CLOSURE_CONTRACT.md
- docs/RELEASE_CHECKLIST.md
- docs/SELLER_CHECKLIST.md

---

**Release boundary:** RC with SHA-bound Disclosure only. No production certification, no independent-review claim, and no claim that prior-subject Gate evidence is bound to the RC artifact baseline or this documentation correction.
