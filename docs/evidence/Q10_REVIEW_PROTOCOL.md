# Q10 Independent Review and Owner Approval Protocol

The Q10 scanner artifact is immutable and remains `gate_result=NOT_VERIFIED`. The final release provenance verifier calculates effective Q10 approval only from GitHub API-backed human attestations on the closure PR.

## Independent reviewer — GitHub PR review

A repository collaborator or organization member other than the Owner must submit an **APPROVED** review on the final PR head. The review body must contain all of these exact markers and values:

```text
CKNEXUS-Q10-REVIEW-APPROVED
COVERAGE-REVIEWED
FINDINGS-REVIEWED
NON-EQUIVALENCE-ACKNOWLEDGED
Candidate SHA: <40-character Q10 evidence source_sha>
Report SHA-256: <64-character Q10 security_report_sha256>
```

The reviewer must assess scanner configuration, coverage, findings, false-positive handling, unresolved risks, and the fact that the open-source layered toolset is not claimed to be equivalent to Codex Security. The review must be submitted after the Q10 scan completed and against the current PR head.

## Owner — final PR issue comment

After the independent APPROVED review, the pinned repository Owner account (`spinlnw10-art`) must post a PR comment containing:

```text
CKNEXUS-Q10-OWNER-APPROVED
Candidate SHA: <40-character Q10 evidence source_sha>
Report SHA-256: <64-character Q10 security_report_sha256>
```

## Automated verification

The release provenance verifier checks the PR is merged into `main`, GitHub identifies the independent reviewer as a `COLLABORATOR` or `MEMBER`, the Owner comment is authored by the repository's pinned Owner login (`spinlnw10-art`), the reviewer and Owner are different accounts, the review/comment URLs and markers match, the review follows scan completion, the Owner comment follows the review, and both attestations bind to the exact candidate SHA and report SHA-256.

No evidence JSON is edited to turn `NOT_VERIFIED` into `PASS`. The final release manifest records the effective Q10 `PASS` and the verified API attestation only after all checks succeed.
