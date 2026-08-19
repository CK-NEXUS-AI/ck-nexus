# Gmail OAuth setup for CK-NEXUS

This guide documents the current canonical CK-NEXUS Gmail OAuth flow. It is Post-P0 integration guidance and is not Q10/Q11/Q12 production evidence.

## Recommended deployment plan

CK-NEXUS should use an environment-specific OAuth model rather than binding Gmail to one host forever:

- **Development / personal testing:** run CK-NEXUS on loopback (`127.0.0.1` or `localhost`). This is the preferred first step because it is free, keeps the runtime private, and does not require a public domain.
- **Staging / remote testing:** deploy the same application behind a managed HTTPS endpoint and inject secrets from the platform secret store. Use a staging OAuth client/project and staging redirect URI.
- **Production / customer use:** use a verified domain, production OAuth client, production secret store, encrypted token persistence, and the normal CK-NEXUS release gates.

Do not reuse development evidence as production release evidence. A localhost Gmail authorization proves the native Gmail integration works in the tested development environment only.

## Security model

- Request the smallest scope set required by the enabled capability.
- Read-only is the default scope: `https://www.googleapis.com/auth/gmail.readonly`.
- Add `https://www.googleapis.com/auth/gmail.send` only when outbound send is intentionally enabled.
- Never commit OAuth client secrets, access tokens, refresh tokens, vault keys, or real `.env.local` files.
- CK-NEXUS code consumes Gmail credentials through `CredentialBroker` leases. Secret values must not be returned by status APIs or logs.
- For persistent authorization, enable the encrypted credential vault before OAuth authorization. A production-like runtime should report encrypted-vault token persistence rather than ephemeral memory.
- Gmail message content is untrusted external data. Attachment handling must remain quarantined/sandboxed according to `creator_app.gmail_governance` policy.
- Prefer a deployment secret manager for remote/staging/production environments. `.env.local` is acceptable only as a protected local development mechanism and must remain outside source control.

## 1. Create or verify the Google OAuth client

Create a Google OAuth 2.0 **Web application** client for the CK-NEXUS deployment. Configure an exact authorized redirect URI matching the CK-NEXUS callback endpoint.

For local development:

```text
http://localhost:8000/api/integrations/gmail/oauth/callback
```

or, if the browser/runtime consistently uses the numeric loopback host:

```text
http://127.0.0.1:8000/api/integrations/gmail/oauth/callback
```

Use exactly the same scheme, host, port, path, and trailing-slash form in Google Cloud and `GMAIL_REDIRECT_URI`. Do not use a wildcard redirect URI.

For staging or production:

```text
https://<ck-nexus-host>/api/integrations/gmail/oauth/callback
```

Use separate development/testing and production OAuth projects/clients when practical so test scopes, test users, consent state, and production verification do not become coupled.

## 2. Configure protected runtime values

The canonical environment names are defined in `.env.example` and consumed through `Settings` / `CredentialBroker`:

```text
CKNEXUS_GMAIL_OAUTH_ENABLED=true
GMAIL_CLIENT_ID=<protected-runtime-value>
GMAIL_CLIENT_SECRET=<protected-runtime-value>
GMAIL_REDIRECT_URI=http://localhost:8000/api/integrations/gmail/oauth/callback
CKNEXUS_GMAIL_SEND_ENABLED=false
```

Enable send only when the test explicitly requires outbound Gmail capability:

```text
CKNEXUS_GMAIL_SEND_ENABLED=true
```

To persist refresh tokens securely, enable the credential vault and provide its encryption key from a protected runtime secret source:

```text
CKNEXUS_VAULT_ENABLED=true
CKNEXUS_VAULT_PATH=data/credential-vault.db
CKNEXUS_VAULT_KEY=<protected-runtime-value>
```

Do not commit the values shown as placeholders.

## 3. Install and start the canonical application

The repository is lockfile-driven. Prefer the frozen `uv` path used by CI rather than an ad-hoc `pip install -r requirements.txt` flow:

```bash
uv lock --check
uv sync --all-extras --dev --frozen
uv run ck-nexus
```

The canonical console entry point is `ck-nexus = main:main`. `main.py` creates the FastAPI app and defaults to host `127.0.0.1` and port `8000` unless `CKNEXUS_HOST` / `PORT` override them.

For local Gmail OAuth, keep the host loopback-only. Do not bind an unauthenticated development instance to `0.0.0.0` merely to complete OAuth.

There is no canonical `creator_app.main:app` module and no canonical `python -m creator_app.connectors.gmail.auth_flow` command in the current repository.

## 4. Verify pre-authorization status

Request:

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

If `CKNEXUS_ACCESS_TOKEN` is configured, call protected CK-NEXUS endpoints with the matching bearer token. Do not disable the access gate just to simplify remote testing.

## 5. Start the OAuth flow

Request:

```text
GET /api/integrations/gmail/oauth/start
```

Open the returned `authorization_url` in the user's normal browser. CK-NEXUS generates a short-lived OAuth state value and requests offline access. After the user grants consent, Google redirects to:

```text
GET /api/integrations/gmail/oauth/callback?code=<authorization-code>&state=<state>
```

The callback validates the state before exchanging the code with Google's token endpoint. Access tokens are held ephemerally with expiry. When a persistent vault is available, refresh tokens are stored through the broker-backed persistent store.

## 6. Verify post-authorization status

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

## 7. Governed Gmail functional verification

Functional verification should cover all of the following without logging raw credentials or unnecessarily persisting raw personal data:

1. Read a controlled test message under an explicit `gmail.read` purpose/consent grant.
2. Treat the message body as untrusted external content; it must never become system/policy authority.
3. Pass personal content through the Privacy Firewall before any external-model route. Verify PII minimization/redaction when external processing is authorized.
4. Verify attachment policy: quarantine is required; executable payloads are rejected; allowed documents are parsed only in the approved sandbox boundary.
5. Create a draft only with approved external-write permission.
6. Send only with both the `gmail.send` capability enabled and explicit send approval.
7. Record redacted evidence: correlation/run ID, purpose, policy decision, message or draft reference, result, and timestamp. Never record OAuth tokens or client secrets.

For attachment testing, use a harmless fixture specifically constructed to exercise the quarantine policy. Do not introduce live malware into the workstation or cloud environment.

## 8. Revoke native CK-NEXUS tokens

Use:

```text
POST /api/integrations/gmail/revoke-local
```

Then confirm `/api/integrations/gmail/status` reports `authorized: false` before treating the integration as disconnected.

## Cloud staging option

Cloud is optional for Step 1. If remote access is required before production, use a staging deployment with:

- managed HTTPS endpoint
- loopback-disabled public runtime only behind CK-NEXUS authentication
- platform secret store for `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and the vault key
- persistent encrypted storage for refresh-token state
- staging-only OAuth client and redirect URI
- least-privilege Gmail scopes
- no development secrets copied into the image or repository
- separate evidence label identifying the environment as staging

This avoids redesign later because the application already reads the redirect URI and credentials from runtime configuration.

## Evidence boundary

A Gmail connection exposed directly to ChatGPT or another external client is separate from the CK-NEXUS native OAuth runtime. A successful external-client send/read smoke test proves only that external client's Gmail connection. It must not be used to claim `GmailOAuthManager` is configured or authorized until the CK-NEXUS status/callback flow above is verified on the actual CK-NEXUS deployment.

Likewise, successful localhost or staging Gmail evidence must not be promoted to Q10/Q11/Q12 release evidence. Production closure remains governed by the dedicated production gates and exact subjects.
