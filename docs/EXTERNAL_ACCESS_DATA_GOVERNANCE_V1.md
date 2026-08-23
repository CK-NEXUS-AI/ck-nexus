# CK-NEXUS External Access & Data Governance Contract v1

Status: Post-P0 development contract. This document does not change production readiness.

## Core rule

CK-NEXUS may access only data for which it has a valid authority path. Public reachability,
connector installation, browser reachability, cached sessions, admin rights, and model/tool
capability are not authority by themselves.

The authority chain is:

`USER INTENT -> ACCESS CLASS -> CONSENT -> SCOPES -> POLICY -> PRIVACY -> EXECUTION -> VERIFICATION -> EVIDENCE`

## Access classes

| Access class | Meaning | Default |
| --- | --- | --- |
| `PUBLIC_WEB` | Content reachable without account authorization | bounded read/search may be allowed by the current user request |
| `AUTHORIZED_CONNECTED` | User-authorized OAuth/connector account data | allow only within active consent and granted scopes |
| `PRIVATE_UNAUTHORIZED` | Private/account data with no current authorized connection | deny |
| `PROHIBITED_BYPASS` | Login, CAPTCHA, ACL, session, credential, or access-control bypass | deny unconditionally |

A user request for public research can serve as bounded read authorization upstream. This
avoids asking again for every public page inside the same clearly scoped task. A private
connected source requires separate connector authorization and active consent.

## Read, store, and mutation are different authorities

- `SEARCH`, `READ`, and verified `INGEST` are read-lane operations.
- `STORE` creates durable retention and therefore requires explicit mutation approval plus a
  retention-policy reference.
- `WRITE`, `SEND`, and `DELETE` require separate explicit mutation approval.
- `WRITE` or `SEND` of non-public data additionally requires a Privacy Firewall disclosure
  decision reference.
- Model reasoning never creates an approval or consent grant.

## Connected private data

Private account access is permitted only through an explicitly authorized connector or OAuth
flow. CK-NEXUS does not require the user's account password to be copied into prompts.
Credentials and tokens must remain behind the Credential Broker/Vault boundary and be exposed
only through consumer-bound leases or provider-managed authorization.

Required conditions for connected reads:

1. current user authorization for the task;
2. connector is authorized;
3. consent reference exists and is still active;
4. required scopes are a subset of granted scopes;
5. the action remains inside the requested purpose.

Revoked or expired consent must deny subsequent access immediately.

## Credential policy

Direct requests for raw passwords, PINs, API keys, refresh tokens, access tokens, private keys,
or session cookies are not an approved access method. There is no bulk credential export lane.
Secret material must not be placed in evidence records or ordinary logs.

OAuth/access tokens may exist operationally behind the Credential Broker because connectors
need credentials to function. The prohibition is on raw secret exposure, uncontrolled storage,
and unauthorized reuse—not on secure brokered authentication itself.

## External-content ingestion

Retrieved content is **data, never authority**. A web page, email, document, MCP result, tool
output, or attachment cannot promote itself into system/developer instructions, create a
permission, approve a write, or request secret disclosure.

Untrusted external content enters quarantine first. Instruction-like content is tainted as a
possible prompt-injection signal. Verification may promote content for processing, but it does
not promote that content into execution authority.

## Data minimization and retention

Evidence should keep identifiers, source, purpose, classification, trust, scopes required,
consent/approval references, content digests, decision result, and timestamps where relevant.
It must not retain raw credentials. Raw source content is not part of the access-decision
record; durable content storage requires its own retention policy and approval.

## Data use versus training

Using authorized data to answer the current task is not equivalent to training or durable
learning. `TRAIN` is denied by this contract and requires a separate explicit data-use policy,
consent model, retention basis, and verification path.

## Egress

Sending, posting, uploading, or otherwise disclosing non-public user data to an external
service requires both mutation approval and a valid Privacy Firewall disclosure decision.
Users can deny or revoke future access; revocation must not be overridden by model preference,
connector reachability, or cached capability.

## Evidence schema

The decision record is deterministic and redacted. It includes:

- schema and request ID;
- source and access class;
- action and purpose;
- data classification and source trust;
- user/connector authorization state;
- required scopes and granted-scope count;
- consent, approval, privacy, and retention references;
- optional content digest;
- outcome and reason;
- CK-NEXUS authority marker;
- explicit `raw_credentials_persisted=false` and `raw_content_persisted=false`;
- SHA-256 decision digest.

## Non-goals

This contract does not implement CAPTCHA solving, authentication bypass, session hijacking,
robots-evasion, hidden background crawling, credential harvesting, or arbitrary account access.
It also does not grant production authority to any browser, connector, model, agent, or tool.

## Integration points

The contract composes with existing CK-NEXUS systems rather than replacing them:

- Connector Fabric: connector/tool activation and one-time execution grants;
- Personal Intelligence: granular grant/revoke consent semantics;
- Privacy Firewall: classification, redaction, and external disclosure decisions;
- Credential Broker: least-privilege, consumer-bound secret leases;
- Evidence Ledger: append-only verification and audit identity.

## Required runtime sequence

```text
User request
  -> classify source/access
  -> reject bypass/private-unauthorized paths
  -> verify task authorization
  -> if connected: verify connector + active consent + scopes
  -> if external content: quarantine/verify before Core use
  -> if durable store: require approval + retention reference
  -> if write/send/delete: require explicit mutation approval
  -> if non-public egress: require Privacy Firewall decision
  -> execute through governed adapter
  -> verify result
  -> append redacted evidence
```
