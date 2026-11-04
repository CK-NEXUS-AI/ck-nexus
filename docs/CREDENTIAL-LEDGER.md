# CK-NEXUS Credential Ledger

**Snapshot:** 2026-10-12  
**Source:** read-only inspection of n8n instance `cknexus2.app.n8n.cloud`; detailed snapshot is recorded in [Master Recovery Ledger](MASTER-RECOVERY-LEDGER.md) on its review branch.  
**Purpose:** track credential *references and evidence*, never secret values.

## Safety rules

- Never export, log, commit, or return OAuth tokens, refresh tokens, API keys, authorization headers, email bodies, or secret-bearing credential fields.
- A credential's presence is not proof of authentication health.
- An execution that returned items proves only that route worked for that execution, account, scope, and time.
- Record timestamps, workflow/execution IDs, sanitized outcomes, and evidence references. Keep raw mailbox data out of this ledger.
- Use `NOT_VERIFIED` rather than inferring health from a credential name or count.

## Snapshot inventory

The read-only n8n credential listing returned 5 Gmail OAuth2 metadata records and 5 Microsoft Outlook OAuth2 metadata records. This is an inventory count, not a claim that all ten credentials are valid or used by the five workflows inspected.

| Account/route label | Evidence | State | Limitation / next check |
|---|---|---|---|
| `spinlnw10@gmail.com` | Email Tools execution #48 returned one item; Radar execution #52 returned two items | `EXECUTED` | Read route evidenced in those runs; refresh/current OAuth health and other actions remain NOT_VERIFIED |
| `toyotati.love@gmail.com` | Radar execution #52 returned two items | `EXECUTED` | Validate current read-only route and map credential ID to account without exposing secrets |
| `toyotati1203@gmail.com` | Radar execution #52 returned two items | `EXECUTED` | Same limitation |
| `chokmantol@gmail.com` | Radar execution #52 returned one item | `EXECUTED` | Same limitation |
| `zfixyzfwbkjq450` | Radar execution #52 returned two items; label does not establish full email identity | `EXECUTED` for Radar route | NOT_VERIFIED for account identity and Email Tools route; label absent from current Email Tools allowlist |
| Microsoft Hotmail | Diagnostic execution #67 returned zero matching rows | `NOT_VERIFIED` for mailbox completeness | Separate OAuth/access verification from query/filter diagnosis |
| Outlook route `outlook` | Node/route exists in Email Tools definition | `NOT_VERIFIED` | No account-specific successful read evidence in inspected executions |
| Outlook route `outlook2` | Node/route exists in Email Tools definition | `NOT_VERIFIED` | No account-specific successful read evidence in inspected executions |
| Remaining Outlook credential metadata | Credential listing found records; no successful account-specific read linked in the inspected runs | `NOT_VERIFIED` | Map IDs/names to intended mailbox under least privilege; never disclose secret values |

## Route mismatch

Radar has five Gmail scan paths; the Email Tools account allowlist contains four Gmail labels plus `outlook` and `outlook2`. The `zfixyzfwbkjq450` label appears in the Radar route but not the Email Tools allowlist. Treat this as a routing/identity reconciliation issue, not an invitation to add the route automatically.

## Required account verification protocol

1. Confirm the intended mailbox identity from non-secret metadata and an authorized owner.
2. Confirm credential type, scope, owner/project and last-updated metadata without reading secret fields.
3. Execute a read-only query limited to minimal metadata and a small bounded time window.
4. Record workflow ID, execution ID, UTC timestamp, sanitized item count, result classification and evidence reference.
5. Mark `VERIFIED` only when the exact claim has adequate evidence. Keep OAuth health, read access, draft creation, send authorization and delete/reply permissions as separate capabilities.
6. Do not test send/draft/delete/reply capabilities as part of this read-only protocol.

## Machine-readable status vocabulary

Use one of: `VERIFIED`, `EXECUTED`, `NOT_VERIFIED`, `BLOCKED`, `REVOKED`, `DISABLED`. Never use `PRODUCTION` as a credential health status. Credential records must contain a reference/ID and metadata only, not credential payloads.
