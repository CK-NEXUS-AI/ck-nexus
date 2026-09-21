# CK-NEXUS Q10 Sale Validation Evidence

Date: 2026-09-22 UTC
Validation subject: sale/q10-validated-20260922

## Exact source
- Repository: /opt/ck-nexus-q10
- Base remediation subject: fbdaec6b4783c3e37f9d33ddead7c863bbe51335
- Validation branch: sale/q10-validated-20260922
- Final commit and tree hash are recorded below after commit.

## Validation performed
- Pytest collection: 238 tests
- Full pytest: 238 passed, 1 warning, exit 0
- Ruff: PASS after minimal lint remediation; E501 is explicitly non-gating in pyproject.toml
- Bandit: PASS at HIGH/MEDIUM threshold (-lll), exit 0
- pip-audit: PASS — No known vulnerabilities found
- git diff --check: PASS

## Scope
This validates the Q10 remediation branch as a tested sale-candidate source state. It does NOT prove Q10 production readiness.

## Remaining gates
- Q10 deep security gate: NOT_VERIFIED
- Q11 live provider: BLOCKED until live provider credential/configuration evidence exists
- Q12 delegated cgroup v2: BLOCKED until required delegation evidence exists
- Production certification: NOT CLAIMED

## Commercial boundary
The accompanying seller-pack is a seller-side commercial package. It must not be interpreted as proof of production certification or as evidence that the 669-test DeepSeek/free-processing repository is the Q10 product.

## Integrity
Final commit and tree hashes must be recorded after commit.

## Final integrity after validation
- Exact validated commit: d377527182e43600d789a14f8b1fa1d824393462
- Exact Git tree: 67eb6739728aed81ea4c810ef7de94ae27501b96
- Seller-pack aggregate SHA-256: c9e3277d20b5e3ee4296479f85b56a87580a1d8e12ed95d3b16c498cdab06453
- Exact-source full pytest at this commit: 238 passed, 1 warning, exit 0
- Ruff: exit 0
- Bandit HIGH/MEDIUM threshold: exit 0
- pip-audit: no known vulnerabilities, exit 0
- git diff --check: exit 0
