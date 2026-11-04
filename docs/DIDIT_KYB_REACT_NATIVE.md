# Didit KYB React Native Integration

Status: development candidate; separate from frozen Q10 evidence.

## Scope

- KYB workflow: `d483655c-0adf-4c47-9d5f-b370d16aece8`
- Backend: CK-NEXUS FastAPI
- Client: Expo / React Native
- Decision authority: verified Didit webhook only
- Didit API keys remain server-side only.

## Server secrets

Configure at runtime only:

```bash
DIDIT_API_KEY=
DIDIT_WEBHOOK_SECRET=
```

Do not commit real values. The workflow ID is pinned in code/config and is not a secret.
## Backend routes

### Create native KYB session

`POST /api/v1/verification/didit/kyb/session`

The route requires trusted CK-NEXUS gateway identity headers. The gateway derives
tenant/actor identity from the authenticated JWT and injects the trusted headers.
The backend returns only:

```json
{"session_id":"...","session_token":"..."}
```

The Didit API key is never returned to the mobile client.

### Webhook

`POST /api/webhooks/didit`

Order of checks:

1. X-Timestamp freshness <= 300 seconds
2. canonical JSON serialization
3. HMAC-SHA256 constant-time verification of X-Signature-V2
4. event_id idempotency
5. exact case-sensitive status state update
6. immediate 2xx response
## React Native client

The Expo app lives at `clients/ck-nexus-mobile`.

Installed package:

`@didit-protocol/sdk-react-native@4.7.6`

The installed package exports `startVerification(token)`. Its actual package
typing differs from the supplied integration snippet that used `DiditSdk`.
The implementation follows the installed package API verified by TypeScript.

The client displays consent/disclosure before enabling verification. SDK completion
is only a UI hint; it never marks the business approved.

## Verification completed

- Python integration/regression tests: 35 passed
- New Didit Python lint: pass
- React Native TypeScript: pass
- Expo Doctor: 21/21 pass
- Didit secret prefix scan: no exposed key value found
## Known limits before live activation

- No live KYB session has been created.
- No paid Didit action has been triggered.
- A real DIDIT_WEBHOOK_SECRET is still required from the Didit webhook destination.
- A public HTTPS webhook route must be deployed before registering the destination.
- The mobile caller must obtain a real CK-NEXUS JWT from the application auth layer.
- npm audit reports 11 moderate issues in the Expo/config-plugin dependency chain.
  The available full remediation is breaking, so no force downgrade was applied.

These limits do not affect Q10 authority state.
