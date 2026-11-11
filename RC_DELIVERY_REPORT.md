# CK-NEXUS Release Candidate — Delivery Report

**Report date:** 2026-11-11
**Decision reference:** Owner-approved Plan A — RC with Disclosure (2026-11-11)
**Base commit before disclosure:** `f8c8b08d1f456d38d6ff30b9f1f2ebb0456ff6b6`
**Base tree before disclosure:** `bf3c2839f0bc2c39139f7228c52c3411a41fea86`
**RC branch:** `fix/pr365-office-archive-hardening-20261111`
**Final RC commit/tree:** This report is included in the final RC commit. Resolve the immutable final values with `git rev-parse HEAD` and `git rev-parse 'HEAD^{tree}'` after commit; those values are also recorded in the delivery message accompanying this artifact.

---

## 1. Artifact Scope

This artifact closes Phase 1 as a **Release Candidate with Disclosure**. It is intended for technical evaluation, due diligence, and deployment planning with explicit buyer verification obligations.

It is **NOT Production Ready** and **NOT Certified 100%**. This disclosure does not convert prior-candidate evidence into evidence for the final RC commit.

## 2. Gate Status and Evidence Provenance

The evidence files below are present in the base candidate. The Q10 attestation and Q11 evidence identify source subject `a31f82d1d45c3398ae14fb506d0893f67a55234d` and tree `686746bb33fe91cfb1134cabfea178646c73519c`. The PR #366 evidence inventory states that Q10–Q16 artifacts are bound to that prior source subject and manifest, not to the final RC disclosure commit.

| Gate | Disclosed status | Evidence / provenance | Buyer action |
|---|---|---|---|
| Q10 Security Review | Owner attestation signed; scanner report is NOT_VERIFIED; independent review outstanding | `evidence/Q10_REVIEW_ATTESTATION.md`; prior subject `a31f82d...` | Obtain independent review on the exact purchased commit |
| Q11 Live Provider | PENDING / BLOCKED; live-provider verification incomplete | `evidence/Q11_OPENAI_LIVE.json`; prior subject `a31f82d...` | Complete live verification with a buyer-controlled funded provider key |
| Q12 Delegated cgroup v2 | Prior-candidate PASS | `evidence/Q12_CGROUP_V2.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |
| Q13 PostgreSQL DR | Prior-candidate PASS_CANDIDATE | `evidence/Q13_POSTGRES_DR.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |
| Q14 Observability | Prior-candidate PASS | `evidence/Q14_OBSERVABILITY_ALERT.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |
| Q15 Clean Machine | Prior-candidate PASS_CANDIDATE | `evidence/Q15_CLEAN_MACHINE.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |
| Q16 Production Image | Prior-candidate PASS_CANDIDATE | `evidence/Q16_PRODUCTION_IMAGE.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |
| Q16 Runtime Licenses | Prior-candidate PASS | `evidence/Q16_RUNTIME_LICENSE_SUMMARY.json`; prior subject `a31f82d...` | Re-verify on the exact purchased commit |

**Important:** The signed Q10 document is an Owner Attestation, not an Independent Review. The Q10 attestation and Q11 JSON both name prior source SHA `a31f82d1d45c3398ae14fb506d0893f67a55234d`. Do not represent them as exact-subject evidence for `f8c8b08` or for the final RC commit.

## 3. CI on the Pre-Disclosure Candidate

GitHub check runs were confirmed on exact candidate SHA `f8c8b08d1f456d38d6ff30b9f1f2ebb0456ff6b6`:

- **test:** SUCCESS — [run 42926259903](https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42926259903)
- **preflight:** SUCCESS — [run 42926259796](https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42926259796)
- **attack-regression:** SUCCESS — [run 42926259778](https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/42926259778)

These three successful CI checks apply to the pre-disclosure candidate `f8c8b08`. They do not apply to the new commit containing this README and report, and they do not establish Q10–Q16 closure.

No Q10–Q16 Gate was run as part of this Phase 1 closeout. Any CI automatically triggered by the requested push is separate from a manual Gate execution.

## 4. Buyer Verification Obligations

Before any production deployment, the buyer must:

1. Obtain an independent Q10 security review and owner approval against the exact purchased commit.
2. Complete Q11 live-provider verification using a buyer-controlled, funded provider credential handled only through an approved secret store.
3. Re-verify Q12–Q16 against the exact purchased commit and preserve each evidence artifact, subject SHA, tree, manifest, and run reference.
4. Verify CI and dependency/security checks on the exact purchased commit.
5. Review the Q10–Q16 Closure Contract, Release Checklist, Seller Checklist, and all disclosed limitations before deployment.

## 5. Honest Assessment

This RC provides the source-code candidate and the preserved implementation/evidence history for technical evaluation. The available records do not establish independent security review, successful live-provider verification, or complete exact-subject Q10–Q16 evidence for the final RC commit. Buyers must perform the stated verification before production use.

No market valuation, resale percentage, or guaranteed sale price is asserted by this report.

## 6. Disclosure Documents

- `evidence/Q10_REVIEW_ATTESTATION.md`
- `evidence/Q11_OPENAI_LIVE.json`
- `docs/Q10_Q16_CLOSURE_CONTRACT.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/SELLER_CHECKLIST.md`

---

**Release boundary:** RC with Disclosure only. No production certification, no independent-review claim, and no claim that prior-subject Gate evidence is bound to the final RC commit.
