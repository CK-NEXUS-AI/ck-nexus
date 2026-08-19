# CK-NEXUS Twin Dialogue Bridge

Status: Post-P0 / DEVELOPMENT ONLY. This bridge is not production-closure evidence and must not change Q10/Q11/Q12, provenance, Final Production Package, or PR #14 state.

## Purpose

Allow two authorized ChatGPT/agent sessions to collaborate through one shared, append-only MCP mailbox while CK-NEXUS remains the sole authority for state, permissions, policy, execution and release decisions.

A ChatGPT shared link is treated only as a context reference/snapshot. It is not a live bidirectional transport. To make two sessions actually exchange messages, both sessions connect to the same remote MCP endpoint and use the same `conversationId`.

Default conversation:

```text
cknexus-dual-dev
```

## Tools

- `twin_status` — read-only bridge/authority status
- `twin_import_context` — store a user-authorized text snapshot; `sourceUrl` is metadata only and is never fetched
- `twin_post` — append proposal, critique, evidence request/response, handoff, decision recommendation, or status
- `twin_read` — read recent records and verify SHA-256 integrity
- `twin_ack` — append an acknowledgement; acknowledgement is not release approval

All records are forced to:

```text
classification=DEVELOPMENT_ONLY
authority=ADVISORY_ONLY
production_evidence=false
```

## Security model

1. Loopback bind is the default.
2. A non-loopback bind is refused unless `CKNEXUS_TWIN_BRIDGE_TOKEN` is configured.
3. Secret-like content is rejected before persistence, including common provider API keys, Telegram bot tokens, AWS access keys, JWTs, Bearer tokens and private keys.
4. The bridge never fetches `sourceUrl`; this avoids turning chat-supplied URLs into an SSRF/open-fetch surface.
5. Dialogue is append-only JSONL with per-record SHA-256 integrity digest.
6. Peer labels are advisory labels, not authenticated authority identities.
7. No tool in this bridge can merge, deploy, tag, modify release evidence, change secrets, execute shell commands, call providers, or promote a production gate.
8. Frozen production closure remains independent from this development branch.

## Start locally

```bash
cd integrations/twin-dialogue-bridge
npm install
npm run typecheck
npm test
npm start
```

Default endpoint:

```text
http://127.0.0.1:18927/mcp
```

Local state:

```text
.cknexus-twin-dialogue.jsonl
```

The state file and `.env` are gitignored.

## Remote connection

ChatGPT requires a remote MCP endpoint rather than direct localhost access. Put the local bridge behind an authenticated private/secure MCP tunnel or another controlled HTTPS boundary. Do not expose port 18927 directly to the public internet.

Both peer sessions must connect to the same endpoint and use the same conversation ID. Suggested labels:

```text
cknexus-canonical
peer-development
```

## Pair-development protocol

Peer A:

1. `twin_status`
2. `twin_read(conversationId="cknexus-dual-dev")`
3. `twin_post(intent="proposal", ...)`

Peer B:

1. `twin_status`
2. `twin_read(conversationId="cknexus-dual-dev")`
3. `twin_post(intent="critique", causationId=<proposal record id>, ...)`
4. optionally send `evidence_request` / `evidence_response`
5. send `decision_recommendation`

CK-NEXUS then independently evaluates recommendations through its normal policy/governance path. A peer recommendation can never self-authorize execution.

## Using the supplied shared ChatGPT conversation

The user-supplied shared conversation URL may be recorded as `sourceUrl`, but the actual text snapshot must be explicitly supplied/imported by an authorized user/session. This bridge intentionally does not scrape or mutate another ChatGPT conversation.

Example conceptual import:

```text
twin_import_context(
  conversationId="cknexus-dual-dev",
  peerLabel="peer-development",
  sourceUrl="<shared conversation URL>",
  snapshotText="<authorized conversation summary or exported text>"
)
```

## Current development/release boundary

Development base when this bridge was created:

```text
2e9d529c4167afd8bc5b0148014f834751e156b5
```

Frozen release source remains:

```text
39f5c1adb9d761ab418cf088ff1f051b1ca731d1
```

Frozen release subject remains:

```text
89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52
```

Production status remains NO-GO until genuine Q10 -> Q11 -> Q12 -> provenance -> checksummed Final Production Package closure succeeds.
