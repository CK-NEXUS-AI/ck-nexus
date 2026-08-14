# CK-NEXUS Connector Runtime Status

Status taxonomy:

- `VERIFIED_CONNECTED` — live read probe succeeded in this ChatGPT runtime.
- `UNBOUND_EXTERNAL_CLAIM` — another environment reported success, but this runtime cannot verify it.
- `NOT_FOUND_CURRENT_RUNTIME` — no matching installable/runtime connector was found here.
- `BLOCKED_OWNER_OAUTH` — connector exists elsewhere but owner consent/login is still required.

## Verified in this runtime

- Gmail — VERIFIED_CONNECTED
- Google Calendar — VERIFIED_CONNECTED
- Google Drive / Sheets — VERIFIED_CONNECTED
- Slack — VERIFIED_CONNECTED
- GitHub — VERIFIED_CONNECTED
- Linear — VERIFIED_CONNECTED
- Notion — VERIFIED_CONNECTED
- Outlook Email — VERIFIED_CONNECTED
- Outlook Calendar — VERIFIED_CONNECTED
- Wix — VERIFIED_CONNECTED

## External claims from Solas/Base44 conversation

The following were reported as connected in the external Solas/Base44 environment, but are not exposed for live verification in this ChatGPT runtime and therefore remain `UNBOUND_EXTERNAL_CLAIM` here:

- Google Analytics
- LinkedIn
- Instagram Business
- TikTok
- Square

## Gorgias

Owner-provided workspace subdomain: `myshop-1-2` (workspace URL form: `myshop-1-2.gorgias.com`).

Current ChatGPT runtime marketplace search for `Gorgias` and `plugin_name:Gorgias OR plugin_description:Gorgias` returned no installable connector. Status here: `NOT_FOUND_CURRENT_RUNTIME`.

This does not mean Gorgias is unavailable in Base44/Solas. The final OAuth/Connect step must be completed in the environment that exposes the Gorgias connector. Never place an API key in the subdomain field.

## Policy

Connector health and auth state must be runtime-scoped. A success report from one environment must not be promoted to another environment without a live probe or signed evidence. OAuth consent, account creation, credential creation/rotation, and permission elevation remain owner-gated. Gmail may be used as an event/notification hub but must not be used to bypass third-party authentication.
