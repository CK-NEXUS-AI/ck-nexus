# CK-NEXUS Error Alert Verification Plan

**Workflow:** `ASq906OfEaDqjDqGug`  
**Observed ID in current n8n snapshot:** `ASq906OfEaDqjDqGug`  
**Snapshot:** 2026-10-12  
**Current status:** `NOT_VERIFIED` for end-to-end alert delivery.

## What is known

- Workflow definition contains Error Trigger → redaction → email alert.
- Workflow was Active during read-only inspection.
- Manual execution #57 was reported successful.
- A manual execution is not proof that a real error event from another workflow triggers delivery.
- No genuine staging failure-injection receipt was established during this review.

## Safety constraints

- Do not deliberately fail a production workflow.
- Do not run the alert workflow with an ordinary Execute action as a substitute for an Error Trigger test.
- Do not send a test alert to an unconfirmed recipient.
- Never include raw exception strings, credentials, tokens, message bodies, or request headers in alert payloads.
- Require an approved isolated staging workflow, a designated test recipient, a rollback/cleanup plan, and explicit authorization before injection.

## Verification steps

1. **Static linkage review:** inventory workflows expected to report errors and inspect their configured error-workflow references read-only.
2. **Redaction review:** verify allowlisted fields only; test that secret-like values and raw stack/error payloads are removed before delivery.
3. **Staging fixture:** create/use a dedicated non-production workflow with no business side effects and an explicit test-run marker.
4. **Approval gate:** obtain owner approval for the exact workflow, failure mode, time window, recipient and cost/side-effect boundaries.
5. **Failure injection:** cause one controlled, deterministic error only in the approved staging fixture.
6. **Receipt capture:** capture the provider delivery result and a sanitized recipient-side receipt with UTC timestamps and correlation ID. Do not record message contents beyond the test marker.
7. **Evidence integrity:** hash the sanitized evidence artifact, record tool/run IDs and source revision; do not claim a signature unless a real signature was generated and verified.
8. **Negative tests:** verify no alert is sent for a successful run and no raw secrets are included. Use a test mailbox and approved bounded test matrix.
9. **Independent review:** a second reviewer confirms trigger wiring, redaction, receipt and evidence linkage.
10. **Update status:** mark `VERIFIED` only for the tested alert path and revision; all other workflows remain `NOT_VERIFIED` until separately covered.

## Evidence record minimum

- incident/correlation ID
- source workflow ID and exact revision/version
- error-workflow ID and exact revision/version
- staging environment identity
- approval reference and approver
- injection timestamp and result
- provider delivery result and sanitized receipt reference
- redaction test result
- artifact digest and verifier identity
- limitations and reviewer decision

## Pass criteria

PASS requires a controlled staging failure, correct Error Trigger routing, successful receipt by the approved operator, verified redaction, and traceable evidence bound to the tested workflow revision. Static wiring, a successful manual execution, or an alert-node success alone is insufficient.
