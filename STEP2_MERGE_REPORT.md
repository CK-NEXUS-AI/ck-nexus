# CK-NEXUS Step 2 Recovery Merge Report

Canonical subject:
- Commit: `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
- Tree: `25d9c74db2b553667ad085172f8ac7beff4146aa`
- Canonical files: 531

Recovery comparison:
- Files compared: 216
- Mapped same: 5
- Mapped conflicts: 26
- Recovery-only: 185

Merge policy:
- Canonical wins every mapped conflict.
- Recovery conflict copies are preserved only in the downloadable quarantine candidate; they are not activated in runtime.
- Identical recovery copies are skipped to avoid duplication.
- Recovery-only material remains inactive pending dedup, tests, security review and adoption review.

Branch: `feature/merge-history-package`

Governance remains:
- Q10 NOT_VERIFIED
- Q11 BLOCKED
- Q12 BLOCKED
- Production NO-GO / NOT CERTIFIED
