# Independent Evidence Reviewer Charter

**Applies to:** CK-NEXUS Q10–Q16 evidence closure and any release-readiness decision.  
**Decision authority:** Evidence acceptance/rejection only, within the approved governance policy.  
**Production authorization:** Not granted by this charter or by a reviewer signature alone.

## 1. Purpose

The independent reviewer decides whether submitted evidence is authentic, complete, correctly bound to the frozen source identity, and sufficient under the documented gate acceptance criteria. The reviewer must be able to reject evidence without retaliation or pressure to achieve a passing result.

## 2. Independence requirements

The reviewer must be a named, accountable human authorized by the project's governance owner and must not have performed any of the following for the evidence under review:

- authored or materially changed the implementation being evaluated;
- operated the relevant scan, runtime, runner, alert injection, or release process;
- assembled or transformed the evidence package in a way that could conceal failures;
- approved the same gate result earlier in the same review chain;
- controlled the credentials or provider account used to produce the result without an independent counter-check.

A reviewer may be technically assisted by tools or AI, but a tool, model, service account, workflow, or the same agent that authored the package cannot satisfy the human-independence requirement. Where organizational size makes full separation difficult, declare the conflict, appoint a second human reviewer, and require a documented compensating control; do not silently waive independence.

## 3. Authority and limits

The reviewer may:

- accept or reject individual artifacts and gate closures;
- request original logs, immutable artifact links, source/tree proofs, signatures, run IDs, or re-execution;
- mark evidence INCOMPLETE, CONFLICTING, STALE, NOT_BOUND, or NOT_VERIFIABLE;
- require a new run against the frozen candidate;
- block a release recommendation when a required control is unmet;
- record dissent and escalate unresolved disputes to the governance owner.

The reviewer may not, by virtue of this role alone:

- access or disclose secret values;
- bypass policy, billing/quota, identity, or audit controls;
- rewrite source evidence, alter run results, or delete failed attempts;
- merge code, deploy services, or promote production unless separately granted that authority under a distinct approved role and change record;
- approve their own implementation or operational execution.

## 4. Evidence review checklist

For each artifact, the reviewer checks:

1. **Identity:** exact full commit SHA, tree SHA, branch/ref, and current candidate freeze.
2. **Authenticity:** original source URI, provider run ID, signature and trusted key policy where required.
3. **Integrity:** artifact digest recomputed from the actual artifact; signature verification result retained.
4. **Execution:** actual run evidence, start/end times, executor identity, tool version, and exit code.
5. **Completeness:** full output and expected test/scan scope; no quota failure, cancellation, truncation, or missing receipt represented as success.
6. **Policy:** result meets the current written gate acceptance criteria, not merely a label such as PASS_CANDIDATE.
7. **Lineage:** artifact's source/tree exactly matches the frozen candidate or has a documented and approved applicability rationale.
8. **Separation:** executor and evidence author are distinct from reviewer.
9. **Limitations:** failed attempts, exclusions, suppressions, access errors, and residual risks are visible.
10. **Decision consistency:** status is consistent across the evidence register, gate report, release status, and PR checks.

Any material mismatch is a rejection or hold, not an invitation to edit the record until it looks consistent.

## 5. Decision semantics

- **ACCEPT:** all mandatory checks pass and the evidence is sufficient for the specific gate. This is not a production authorization.
- **REJECT:** one or more mandatory conditions fail, evidence conflicts, or evidence is misrepresented.
- **HOLD / NEEDS EVIDENCE:** a required source, run, permission, receipt, or independent verification is missing.
- **NOT APPLICABLE:** allowed only when the written policy explicitly permits it and the policy owner approves the rationale.

Silence, workflow success, hash equality, or lack of findings does not imply acceptance.

## 6. Reviewer decision form

Complete this form as a human reviewer. Do not pre-fill a passing decision.

```yaml
review_id: "<unique review ID>"
reviewer:
  legal_or_organizational_identity: "<human name and role>"
  organization: "<organization/team>"
  declared_conflicts: []
  independence_attestation: false
review_scope:
  repository: "spinlnw10-art/ck-nexus"
  candidate_commit: "cb612b72304246781b7dab48dad77d227c40d45d"
  candidate_tree: "20f2073aae91a586619e91bbfd33cc93ab9da872"
  gates_reviewed: ["Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q16"]
evidence_review:
  - gate: "Q10"
    artifact_uri: "<immutable source URI>"
    artifact_sha256: "<recomputed digest>"
    source_commit: "<full SHA>"
    source_tree: "<full tree SHA>"
    decision: "HOLD"
    rationale: "<factual reason>"
overall_decision: "HOLD"
production_authorization: false
reviewed_at_utc: "<ISO-8601>"
reviewer_signature_or_approved_attestation: "<approved signature reference>"
```

The sample `HOLD` for Q10 is illustrative of the currently reported incomplete scan, not a completed human review. The reviewer must replace it with their own evidence-based decision after inspecting the actual artifacts.

## 7. Escalation and record retention

- Retain submitted artifacts, failed attempts, review notes, and decisions in access-controlled immutable storage according to the project's retention policy.
- Record who submitted, executed, reviewed, and accepted each artifact.
- If the reviewer finds tampering, secret exposure, or evidence misrepresentation, stop the closure workflow and escalate through the security incident process.
- Re-review is required when the candidate SHA/tree changes or an artifact is regenerated.
- Store reviewer signatures/attestations by reference; never paste private keys or secret credentials into the repository.

## 8. Final guardrail

**A reviewer can accept evidence; only the documented release governance process can authorize a release.** Until all required gates are VERIFIED on the approved release identity and required human approvals are recorded, CK-NEXUS remains **Production NO-GO**.
