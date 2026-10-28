# CK-NEXUS Gmail OAuth Connect Button — Design

**Date:** 2026-10-26  
**Status:** Implemented in repository; live deployment not yet available.

## Goal
Provide a visible “เชื่อมต่อ Gmail” button in the CK-NEXUS Full System dashboard. The button must initiate Google's official OAuth consent flow, exchange the one-time authorization code on the server, store credentials through the existing Credential Broker/Vault boundary, and report CONNECTED only after a live read-only Gmail API verification succeeds.

## Architecture
- **Frontend:** `creator_app/web/full-system.html`, `full-system.js`, and `full-system.css` add a Gmail status panel, connect action, refresh action, scope display, and sanitized result output.
- **Authorization start:** `GET /api/integrations/gmail/oauth/start` returns a Google authorization URL; the browser navigates to it only after checking the destination origin is `https://accounts.google.com`.
- **Callback:** `GET /api/integrations/gmail/oauth/callback` validates the one-time state through the existing OAuth manager, exchanges the code server-side, and redirects to `/demo?gmail=connected`, `denied`, or `error`.
- **Verification:** `GET /api/integrations/gmail/test` makes a read-only request to the fixed Google Gmail profile endpoint. Only a successful response returns `read_only_verified=true`.
- **Credentials:** Access and refresh tokens are never returned to the browser. Refresh-token persistence uses the existing encrypted vault when available; otherwise the status explicitly reports ephemeral-memory storage.

## Security boundaries
- Default scope remains `https://www.googleapis.com/auth/gmail.readonly`; sending email is not enabled by this UI.
- Client secret and OAuth tokens remain server-side.
- The verification request is restricted to `gmail.googleapis.com`; refresh requests are restricted to `oauth2.googleapis.com`.
- API status output omits the Gmail address and token material.
- A failed live verification is shown as a failure, not as CONNECTED.
- OAuth state is currently stored in process memory; multi-worker deployment requires a shared state store or a single-worker deployment.

## Validation
- Regression tests cover callback redirect behavior, safe verification output, trusted Google host boundaries, and refresh-token recovery.
- Frontend JavaScript is syntax-checked with Node; Python tests and Ruff are run before claiming completion.

## Deployment prerequisites
The VPS currently runs a standalone `cknexus-api-gateway.service` process from `/usr/local/libexec/cknexus_api_gateway.py` on loopback port 8790. It does not serve `creator_app/api.py` or the Full System dashboard, and no Creator App systemd service was found. Therefore repository changes are not live yet.

Before live use, deploy the Creator App behind an approved HTTPS route and configure:
- `CKNEXUS_GMAIL_OAUTH_ENABLED=true`
- `GMAIL_REDIRECT_URI=https://<approved-host>/api/integrations/gmail/oauth/callback`
- Google OAuth Client ID and Client Secret in the server-side Credential Broker
- encrypted credential vault configuration for persistent refresh-token storage
- the exact same callback URL in the Google Cloud OAuth client allowlist

Do not place a client secret or token in browser storage or chat. Do not enable the send scope unless separately approved.
