# Q10 independent review and Owner approval protocol

The independent reviewer must submit an APPROVED review on the exact closure PR head after the Q10 scan completes. The review body must contain:

- CKNEXUS-Q10-REVIEW-APPROVED
- COVERAGE-REVIEWED
- FINDINGS-REVIEWED
- NON-EQUIVALENCE-ACKNOWLEDGED
- source_sha: exact candidate commit SHA
- source_tree: exact Git tree SHA
- runtime_subject: exact runtime subject manifest SHA-256
- report_sha256: exact Q10 report SHA-256
- workflow_run_id: exact Q10 workflow run ID

The pinned repository Owner (spinlnw10-art) must then add a later PR issue comment containing CKNEXUS-Q10-OWNER-APPROVED and the same five exact identity fields. The reviewer must be a different authenticated repository collaborator/member. The provenance verifier checks the PR head, review commit, actor identities, association, ordering, and every identity field through GitHub's authenticated API. The verifier never accepts a comment or review bound only to a stale ancestor.


The reviewer must also include substantive, non-placeholder values for all five fields below. Each value must describe the actual review performed; a marker-only approval is not sufficient.

- scanner_configuration_review: describe the pinned tools, versions, ruleset identity, scope, and any material exclusions.
- findings_review: summarize the findings and the disposition of each blocking/high-risk item.
- false_positive_handling_review: explain how suspected false positives were assessed and retained or excluded.
- unresolved_risks: identify remaining risks and blockers, or explain why none remain.
- non_equivalence_assessment: explain the limits of the non-Codex toolchain and why it is not represented as Codex Security equivalence.
