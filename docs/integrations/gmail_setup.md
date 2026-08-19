# Gmail OAuth setup for CK-NEXUS

This guide documents the current canonical CK-NEXUS Gmail OAuth flow. It is Post-P0 integration guidance and is not Q10/Q11/Q12 production evidence.

## Security model

- Request the smallest scope set required by the enabled capability.
- Read-only is the default scope: `https://www.googleapis.com/auth/gmail.readonly`.
- Add `https://www.googleapis.com/auth/gmail.send` only when outbound send is intentionally enabled.
- Never commit OAuth client secrets, access tokens, refresh tokens, vault keys, or real `.env.local` files.
- CK-NEXUS code consumes Gmail credentials through `CredentialBroker` leases. Secret values must not be returned by status APIs or logs.
- For persistent authorization, enable the encrypted credential vault before OAuth authorization. A production-like runtime should report encrypted-vault token persistence rather than ephemeral memory.
- Gmail message content is untrusted external data. Attachment handling must remain quarantined/sandboxed according to `creator_app.gmail_governance` policy.

## 1. Create or verify the Google OAuth client

Create a Google OAuth 2.0 Web application client for the CK-NEXUS deployment. Configure an exact authorized redirect URI matching the CK-NEXUS callback endpoint:

```text
https://<ck-nexus-host>/api/integrations/gmail/oauth/callback
```

For a loopback development deployment, use the exact loopback origin and port actually serving CK-NEXUS, for example:

```text
http://127.0.0.1:8000/api/integrations/gmail/oauth/callback
```

Do not use a wildcard redirect URI.

## 2. Configure protected runtime values

The canonical environment names are defined in `.env.example` and consumed through `Settings` / `CredentialBroker`:

```text
CKNEXUS_GMAIL_OAUTH_ENABLED=true
GMAIL_CLIENT_ID=<protected-runtime-value>
GMAIL_CLIENT_SECRET=<protected-runtime-value>
GMAIL_REDIRECT_URI=https://<ck-nexus-host>/api/integrations/gmail/oauth/callback
CKNEXUS_GMAIL_SEND_ENABLED=false
```

To persist refresh tokens securely, enable the credential vault and provide its encryption key from a protected runtime secret source:

```text
CKNEXUS_VAULT_ENABLED=true
CKNEXUS_VAULT_PATH=data/credential-vault.db
CKNEXUS_VAULT_KEY=<protected-runtime-value>
```

Do not commit the values shown as placeholders. Prefer the deployment platform's secret store or another protected runtime injection mechanism over source-controlled files.

## 3. Verify pre-authorization status

Start CK-NEXUS and request:

```text
GET /api/integrations/gmail/status
```

Before authorization, expected conditions are:

- `enabled: true`
- `configured: true`
- `authorized: false`
- scopes contain read-only and contain send only when `CKNEXUS_GMAIL_SEND_ENABLED=true`
- for persistent authorization, `token_persistence: encrypted-vault`

Status output must not include client secrets, access tokens, or refresh tokens.

## 4. Start the OAuth flow

Request:

```text
GET /api/integrations/gmail/oauth/start
```

Open the returned `authorization_url` in the user's browser. CK-NEXUS generates a short-lived OAuth state value and requests offline access. After the user grants consent, Google redirects to:

```text
GET /api/integrations/gmail/oauth/callback?code=<authorization-code>&state=<state>
```

The callback validates the state before exchanging the code with Google's token endpoint. Access tokens are held ephemerally with expiry. When a persistent vault is available, refresh tokens are stored through the broker-backed persistent store.

There is no canonical `python -m creator_app.connectors.gmail.auth_flow` command in the current repository. The canonical flow is the HTTP API implemented by `creator_app.gmail_oauth` and `creator_app.api`.

## 5. Verify post-authorization status

Request the status endpoint again. A successful native CK-NEXUS authorization requires:

```text
enabled: true
configured: true
authorized: true
```

For a production-like persistent integration also require:

```text
token_persistence: encrypted-vault
production_vault_required: false
```

If authorization is revoked or credentials become unavailable, fail closed and do not downgrade to an ungoverned direct credential path.

## 6. Governed Gmail functional verification

Functional verification should cover all of the following without logging raw credentials or unnecessarily persisting raw personal data:

1. Read a controlled test message under an explicit `gmail.read` purpose/consent grant.
2. Treat the message body as untrusted external content; it must never become system/policy authority.
3. Pass personal content through the Privacy Firewall before any external-model route. Verify PII minimization/redaction when external processing is authorized.
4. Verify attachment policy: quarantine is required; executable payloads are rejected; allowed documents are parsed only in the approved sandbox boundary.
5. Create a draft only with approved external-write permission.
6. Send only with both the `gmail.send` capability enabled and explicit send approval.
7. Record redacted evidence: correlation/run ID, purpose, policy decision, message or draft reference, result, and timestamp. Never record OAuth tokens or client secrets.

## 7. Revoke native CK-NEXUS tokens

Use:

```text
POST /api/integrations/gmail/revoke-local
```

Then confirm `/api/integrations/gmail/status` reports `authorized: false` before treating the integration as disconnected.

## Evidence boundary

A Gmail connection exposed directly to ChatGPT or another external client is separate from the CK-NEXUS native OAuth runtime. A successful external-client send/read smoke test proves only that external client's Gmail connection. It must not be used to claim `GmailOAuthManager` is configured or authorized until the CK-NEXUS status/callback flow above is verified on the actual CK-NEXUS deployment.
