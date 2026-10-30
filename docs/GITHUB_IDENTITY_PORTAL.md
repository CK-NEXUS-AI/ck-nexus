# CK-NEXUS GitHub Identity Portal

The /identity page verifies the signed-in GitHub account through GitHub OAuth. It is an identity proof only; it does not authorize VPS, Termux, Gmail, repository writes, or CK-NEXUS privileged actions.

## Configure

1. Create a GitHub OAuth App in GitHub Developer Settings.
2. Set its callback URL to the exact public HTTPS URL: https://YOUR_HOST/api/identity/github/callback
3. Configure these variables in the protected runtime environment (never commit real values):
   - CKNEXUS_GITHUB_OAUTH_ENABLED=true
   - CKNEXUS_GITHUB_OAUTH_CLIENT_ID
   - CKNEXUS_GITHUB_OAUTH_CLIENT_SECRET
   - CKNEXUS_GITHUB_OAUTH_REDIRECT_URI=https://YOUR_HOST/api/identity/github/callback
4. Restart the CK-NEXUS API service through the normal deployment process.
5. Open https://YOUR_HOST/identity and select the GitHub verification button.

The requested scopes are read:user and user:email; no repository write scope is requested. The server exchanges the authorization code, reads /user, discards the access token after the request, and returns only a short-lived identity session cookie. OAuth state and identity sessions are held in process memory and expire after 10 minutes and 30 minutes respectively. This implementation is suitable for controlled single-process use and local verification; production multi-worker deployments should move one-time state and sessions to a shared, TTL-backed store before enabling it.

## Endpoints

- GET /identity — identity portal UI
- GET /api/identity/github/status — redacted identity status
- GET /api/identity/github/start — begin OAuth
- GET /api/identity/github/callback — validate state, exchange code, verify profile
- POST /api/identity/github/revoke — revoke this portal's local identity session

No endpoint returns the GitHub access token. Revoke removes the CK-NEXUS local session; use GitHub account settings to revoke the OAuth App grant itself.

## Evidence boundary

A successful GitHub identity check proves only that the user authenticated to GitHub during that OAuth flow. It does not prove ownership of a separate Gmail account, authorize account-wide email access, or grant access to remote devices. Provider credentials, API access and privileged CK-NEXUS actions remain separately governed.
