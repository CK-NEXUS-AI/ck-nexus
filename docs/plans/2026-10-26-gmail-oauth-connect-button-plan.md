# Gmail OAuth Connect Button — Implementation Plan

- [x] Inspect the existing Gmail OAuth manager, API routes, credential broker, and Full System dashboard.
- [x] Add the Gmail panel and a browser-side connect flow to Google's official authorization endpoint.
- [x] Redirect OAuth callback outcomes back to the dashboard without returning tokens.
- [x] Add a server-side read-only Gmail profile verification endpoint; only verified responses may show CONNECTED.
- [x] Refresh expired/missing access tokens using the brokered refresh token.
- [x] Add regression tests for callback redirects, token redaction, trusted hosts, and refresh behavior.
- [x] Run the focused validation suite: 54 passed.
- [x] Run the full repository suite: 913 passed, 2 skipped, 1 upstream deprecation warning.
- [x] Ruff, Node syntax validation, Gmail DOM selector check, and `git diff --check` passed.
- [ ] Configure Google OAuth credentials and encrypted vault on the deployed Creator App runtime.
- [ ] Deploy the Creator App behind HTTPS; the currently active VPS API gateway is a separate minimal service and does not serve this dashboard.
- [ ] Complete an interactive Google consent test and verify the live Gmail API before reporting production CONNECTED.
