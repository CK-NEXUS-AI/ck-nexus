# CK-NEXUS Hotmail Zero-Results Investigation Ledger

**Incident reference:** `INC-2026-001` (proposed local tracking ID; not an externally assigned incident number)  
**Snapshot:** 2026-10-12  
**Workflow:** `vPc9I9AICVGaeXEK` — CK-NEXUS Hotmail 7-Day Read-Only Diagnostic  
**Related workflow:** `DX6ROxvvgE0iU7K5` — CK-NEXUS AI Ops Radar - Daily Digest

## Current facts

- Diagnostic workflow is inactive.
- Execution #67 completed successfully through the observed integration path.
- Its redacted summary returned `NO_EMAILS_MATCHED` and `count = 0`.
- Radar execution #52 also did not provide useful Hotmail item fields in the inspected output.
- The diagnostic execution's success does **not** establish that the mailbox is empty, that OAuth is healthy, or that the query covered the intended period.

## Status

- Incident state: `OPEN` (proposed investigation state; not yet persisted in a live incident database).
- Severity: `MEDIUM` provisional, pending owner confirmation and impact assessment.
- Technical classification: `NOT_VERIFIED`.
- No remediation or mailbox mutation has been performed.

## Hypotheses to distinguish

| Hypothesis | Read-only evidence needed | Interpretation |
|---|---|---|
| Mailbox has no messages in the period | Confirm account and a known-safe bounded query using a trusted client or approved test mailbox | Only then can zero results be consistent with an empty period |
| Date/window mismatch | Inspect query's cutoff calculation, timezone and received-date fields | A UTC/Bangkok boundary error may exclude expected messages |
| Filter/search mismatch | Inspect sanitized query shape and allowed filters, not message bodies | A too-strict filter can produce zero despite messages existing |
| Credential/scope problem | Inspect sanitized provider error/status and credential metadata; do not reveal token | Distinguish access denied/expired credentials from a legitimate empty result |
| Node output-shape mismatch | Inspect safe field names/counts and branch behavior | Provider items might exist but not be counted or propagated |
| Provider/API transient issue | Inspect execution error metadata and provider status code after redaction | Do not infer this solely from zero rows |

## Safe investigation plan

1. Read the current workflow definition and execution metadata; do not activate or execute it.
2. Record the exact query window, timezone, provider, mailbox label, filter predicates, and node-level item counts.
3. Compare the diagnostic and Radar query windows without reading message bodies.
4. Verify that an approved test mailbox has a known message inside the target window, or ask the owner to confirm a safe expected-result fixture.
5. If a live read test is later authorized, run a bounded read-only query only; no sends, drafts, deletions, replies, attachment downloads or message-content capture.
6. Save sanitized evidence and update the incident status only when the hypothesis is supported.
7. Close only with evidence showing the root cause, fix (if needed), regression result, and no unintended mailbox changes.

## Closure criteria

- Root cause is evidence-backed, or explicitly classified as unresolved.
- The expected-result test has a known, authorized fixture.
- Result count and date boundaries are reproducible.
- No secrets or message content are retained in the ledger.
- A second read-only verification confirms the fix.

**Do not convert `NO_EMAILS_MATCHED` into “mailbox empty” without independent evidence.**
