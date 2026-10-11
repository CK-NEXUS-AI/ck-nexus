# CK-NEXUS Master Recovery Ledger
**Snapshot date:** 2026-10-12 (UTC; n8n instance: `cknexus2.app.n8n.cloud`)  
**Ledger type:** Evidence-indexed status snapshot; not a production certification.  
**Change policy:** Documentation-only. No workflow was activated/edited, no credential secret was read, and no new email was sent during this review.

## 1. Executive decision

- **n8n visibility:** VERIFIED for read-only workflow/credential metadata and selected execution details.
- **Email automation:** PARTIAL. A Gmail read path and the Radar digest run have successful execution evidence; not all accounts or actions are verified.
- **n8n production readiness:** NOT_VERIFIED. Authentication hardening, account coverage, Hotmail result interpretation, schedule timing, and real Error Trigger delivery remain open.
- **CK-NEXUS production:** **NO-GO**. Candidate CI/component results do not equal the complete Q10–Q16 release gate. Do not promote or claim production certification.

## 2. Evidence vocabulary — do not collapse states

| State | Meaning in this ledger |
|---|---|
| **VERIFIED** | The specific claim was checked against returned live metadata or an explicit artifact. The claim is limited to that scope. |
| **EXECUTED** | A recorded workflow/job ran. Execution success is not proof of complete behavior, security, or production readiness. |
| **NOT_VERIFIED** | Evidence is absent, incomplete, stale, ambiguous, or does not cover the required assertion. |
| **PRODUCTION** | Promotion status only. CK-NEXUS remains NO-GO until Q10–Q16 and final immutable release identity converge and are independently verified. |

Rules: SHA MATCH != VERIFIED; LOCAL/CANDIDATE PASS != LIVE PASS; EXECUTED != VERIFIED; CODE != TEST != PRODUCTION; component PASS != gate PASS.

## 3. n8n live snapshot

Read-only connector inspection found **5 workflows**. Exactly **2 were Active** at inspection time. Metadata listed **5 Gmail OAuth2 credentials** and **5 Microsoft Outlook OAuth2 credentials**. Credential existence does not prove OAuth validity or successful access.

| Workflow | ID | Live state | Execution evidence inspected | Current conclusion |
|---|---|---|---|---|
| ChatGPT Tools - All Email Accounts | `nfx2SidgLjMULigp` | Inactive | #48 success: Gmail get_email returned one item for `spinlnw10@gmail.com`; #64 success: invalid account/action rejected | Read path and rejection path EXECUTED successfully; all-account coverage and auth safety NOT_VERIFIED |
| CK-NEXUS Hotmail 7-Day Read-Only Diagnostic | `vPc9I9AICVGaeXEK` | Inactive | #67 integrated execution success; redacted summary `NO_EMAILS_MATCHED`, count 0 | EXECUTED; whether mailbox is empty or query/filter returned no rows NOT_VERIFIED |
| CK-NEXUS AI Ops Radar - Daily Digest | `DX6ROxvvgE0iU7K5` | Active | #52 trigger execution success; Gmail scan nodes returned 2, 2, 2, 1, 2 items; Hotmail scan returned an empty-shaped result; digest reported scannedCount 35, urgentCount 18, opportunityCount 1, failedRoutes 0; send node returned message identifiers | EXECUTED successfully for that run; completeness of all mailboxes and classification accuracy NOT_VERIFIED |
| CK-NEXUS Control Plane - Production Error Alert | `ASq906OfEaDqjGug` | Active | #57 manual execution was reported successful; workflow contains Error Trigger → redaction → email alert | Structure VERIFIED; real failure-to-alert delivery and coverage of all workflows NOT_VERIFIED |
| CK-NEXUS Operations Master - Safe Index | `QYr9oAO6hWv5QcT9` | Inactive | #66 manual execution success; output labels itself `READ_ONLY_INDEX` and warns it is not a live health check | Index generation EXECUTED; not an orchestrator or whole-system health proof |

Workflow links:
- [Email Tools](https://cknexus2.app.n8n.cloud/workflow/nfx2SidgLjMULigp)
- [Hotmail Diagnostic](https://cknexus2.app.n8n.cloud/workflow/vPc9I9AICVGaeXEK)
- [AI Ops Radar](https://cknexus2.app.n8n.cloud/workflow/DX6ROxvvgE0iU7K5)
- [Production Error Alert](https://cknexus2.app.n8n.cloud/workflow/ASq906OfEaDqjGug)
- [Operations Master](https://cknexus2.app.n8n.cloud/workflow/QYr9oAO6hWv5QcT9)

### n8n findings and risks

1. **Email Tools authentication:** webhook node declares `n8nOAuth2`; request validation includes account/action allowlisting and an `approved=true` check for send requests. Workflow remains Inactive. Verify the actual invocation/authentication model and fail-closed behavior before activation.
2. **Account coverage mismatch:** Radar has five Gmail scan paths, including `zfixyzfwbkjq450`; Email Tools allowlist currently names four Gmail accounts plus `outlook` and `outlook2`. The `zfixyzfwbkjq450` route is not in the Email Tools allowlist. Do not assume the five Gmail credentials map one-to-one to all routes.
3. **Sending:** Email Tools send nodes are disabled in the inspected definition. Preserve this until reviewed, approved, and tested; do not run a live send test casually.
4. **Hotmail:** diagnostic count is zero. Radar code explicitly warns that zero metadata results do not establish an empty mailbox. Check filter, received-after window, account selection, and OAuth access.
5. **Schedule:** the schedule node specifies 08:00 daily and `Asia/Bangkok`. Execution #52 was reported as trigger mode at approximately 2026-10-11 21:12 UTC (2026-10-12 04:12 Bangkok), not 08:00. Confirm the raw execution timestamp, timezone settings, and trigger history before claiming schedule correctness.
6. **Error alert:** static wiring and redaction code are present; no genuine failure-injection receipt was established. Do not test by intentionally failing production workflows.
7. **Operations Master:** its own output says it is a navigation/safety registry, not a live health check.

## 4. Email account coverage matrix

| Account/route | Evidence from inspected run(s) | State |
|---|---|---|
| `spinlnw10@gmail.com` | Email Tools #48 read one message; Radar #52 returned two items | EXECUTED; per-account read path evidenced |
| `toyotati.love@gmail.com` | Radar #52 returned two items | EXECUTED in that run |
| `toyotati1203@gmail.com` | Radar #52 returned two items | EXECUTED in that run |
| `chokmantol@gmail.com` | Radar #52 returned one item | EXECUTED in that run |
| `zfixyzfwbkjq450` | Radar #52 returned two items; full email identity not confirmed | EXECUTED in that run; identity and Email Tools route NOT_VERIFIED |
| Microsoft Hotmail | Diagnostic #67 returned zero metadata rows; Radar path returned no useful item fields | EXECUTED; actual mailbox completeness NOT_VERIFIED |
| Microsoft Outlook routes/other Outlook credentials | Credential metadata exists; no account-by-account successful read was established in the inspected runs | NOT_VERIFIED |

No email subject/body, tokens, OAuth secrets, or message contents are stored in this ledger.

## 5. CK-NEXUS release and production gate ledger

Latest candidate evidence was inspected in open PR [#289](https://github.com/spinlnw10-art/ck-nexus/pull/289), whose body declares candidate HEAD `38d3922a0c3fee66a0c795d21cecf3d882973274`, tree `47298755a4cb1d57d468360c9ea728519e9dd9b2`, and manifest SHA-256 `e1af55a922939db3a3933ae2bb2f23d25e2606c5bf7b99a748b23b9c58b54c9b`. These are **PR candidate identity**, not proof of the default branch, deployed VPS, or final release artifact. PR #289 remains a candidate; do not infer it is merged.

| Gate | Latest evidence in candidate report | Canonical gate status |
|---|---|---|
| Q05 | Candidate run 38182839787: 626 passed, 0 failed; compile/Ruff/reviewed Bandit/secret scan reported PASS | Candidate PASS only; rebind to final frozen release |
| Q08 | Live Redis/PostgreSQL idempotency and concurrency evidence reported PASS | Candidate PASS only; rebind to final frozen release |
| Q09 | Trusted identity, unknown-risk DENY, grant consumption and governance regressions reported PASS_CANDIDATE | Candidate PASS only |
| Q10 | Dependency component reports 0 known vulnerabilities, but required native Codex Security Deep Security Scan has not completed | **NOT_VERIFIED / BLOCKER** |
| Q11 | Live OpenAI provider blocked by `credit_balance_exhausted`; expected `cknexus-q11-smoke.service` absent on VPS | **BLOCKED / NOT_VERIFIED** |
| Q12 | Candidate report says required `cknexus-q12` self-hosted runner offline, non-root `cknexus` service account absent, delegated cgroup root owned by `runner:runner` | **BLOCKED / NOT_VERIFIED** |
| Q13 | Isolated PostgreSQL backup/restore reported PASS_CANDIDATE | Candidate only; final release binding required |
| Q14 | Real staging failure injection and operator alert receipt still required | **BLOCKED / NOT_VERIFIED** |
| Q15 | Fresh-host install/runtime smoke reported PASS_CANDIDATE | Candidate only; final artifact binding required |
| Q16 | Production image and runtime license jobs reported PASS/PASS_CANDIDATE; final Q10–Q15 convergence, commercial checks, independent review and immutable release artifact remain open | **BLOCKED / NOT_VERIFIED** |

Related candidate runs reported by PR #289:
- [Q05/Q08/Q09 evidence — run 38182839787](https://github.com/spinlnw10-art/ck-nexus/actions/runs/38182839787)
- [Q10 component/Q13/Q15 — run 38182977812](https://github.com/spinlnw10-art/ck-nexus/actions/runs/38182977812)
- [Q16 candidate image — run 38182984722](https://github.com/spinlnw10-art/ck-nexus/actions/runs/38182984722)
- [Q16 runtime licenses — run 38182991582](https://github.com/spinlnw10-art/ck-nexus/actions/runs/38182991582)

These are reported candidate-run outcomes, not independent proof that every required gate is currently green on one identical frozen source identity. The contract in [docs/Q10_Q16_CLOSURE_CONTRACT.md](Q10_Q16_CLOSURE_CONTRACT.md) requires final convergence.

## 6. Canonical status decision

- **VERIFIED:** read-only n8n metadata retrieval; five named workflows found; two active at inspection; credential metadata counts; the specific node structure and recorded execution summaries described above.
- **EXECUTED:** Email Tools read test #48; invalid-request rejection #64; Hotmail diagnostic #67; Radar trigger #52; Operations Master #66; alert workflow manual execution #57.
- **NOT_VERIFIED:** all-account OAuth health; Outlook per-account read coverage; Hotmail mailbox completeness; Email Tools authentication adequacy and safe activation; correct 08:00 schedule behavior; genuine Error Trigger delivery; Q10 native scan; Q11 live provider; Q12 staging enforcement; Q14 alert receipt; Q16 final convergence.
- **PRODUCTION:** **NO-GO**. No claim of production certification, security certification, or final release is authorized by this snapshot.

## 7. Ordered recovery actions

1. Keep Email Tools inactive and its send nodes disabled. Review webhook authentication, request schema, account allowlist, explicit approval semantics, and rejection-path evidence.
2. Run account-by-account **read-only** Gmail/Outlook checks with redacted evidence and timestamps; reconcile credential names to actual account identity without exposing secrets.
3. Diagnose Hotmail filters and OAuth separately; preserve the distinction between `NO_EMAILS_MATCHED` and “mailbox empty.”
4. Confirm Radar timezone and real scheduled trigger timestamps without manually executing the digest (which sends a real email).
5. In an isolated staging path, test Error Trigger wiring and capture a real operator-alert receipt; never fabricate Q14 evidence.
6. Close Q10/Q11/Q12/Q14 blockers, then re-run/re-bind Q05/Q08/Q09/Q13/Q15/Q16 against one frozen release identity. Require independent review and final signed immutable release artifact before any production decision.

## 8. Review limitations

This ledger combines (a) live read-only n8n connector results from 2026-10-12 and (b) candidate gate details declared in open PR #289 and the repository's Q10–Q16 contract. The candidate CI assertions were not all independently rerun in this review. The ledger is documentation, not a cryptographic evidence bundle; it has not been signed or independently attested. No production mutation was performed.
