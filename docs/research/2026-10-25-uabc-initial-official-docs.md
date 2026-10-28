# UABC initial official-documentation checks

Date checked: 2026-10-25. This is a first-pass evidence note, not exhaustive research of all registry entries.

| Platform | Official source | Evidence / restriction |
|---|---|---|
| GitHub | https://docs.github.com/en/rest | Official REST API and authentication documentation exist. This does not establish that the CK-NEXUS target repository is accessible. |
| Vercel | https://vercel.com/docs/rest-api | Official REST API can manage projects, deployments, domains, environment variables and secrets. Access tokens and rate limits apply. |
| Webflow | https://developers.webflow.com/reference | Official docs list Data API, Designer API, Browser API, SDKs and CLI; each operation has its own supported scope. |
| Bubble | https://manual.bubble.io/core-resources/api | Data API supports read/write data and workflow API can execute workflows when enabled in the application. App configuration and permissions matter. |
| FlutterFlow | https://docs.flutterflow.io/resources/projects/settings/project-apis/ | Project YAML API supports list/read/export/validate/update; official docs say a paid subscription is required. Do not represent this API as free-tier access. |
| Wix | https://dev.wix.com/docs/api-reference/ | Official REST API exists for supported site and business data. OAuth scopes and API-specific permissions apply. |
| Supabase | https://supabase.com/docs/guides/api | Data REST API is generated from the database schema; project URL, API credentials, row-level security and key handling matter. |
| n8n | https://docs.n8n.io/connect/n8n-api/api-reference/ | Official REST API requires an API key; docs list Cloud Starter/Pro/Enterprise and all self-hosted editions, but not the Cloud free trial. |
| Google AI Studio / Gemini | https://ai.google.dev/gemini-api/docs | Official Gemini API docs provide documented model and generation APIs; current quota and billing are account/region/plan dependent. |
| AppGu (Thai) | https://appgu.ai/ | Official site advertises Thai-language AI app generation and three initial credits without a card. Public API documentation was not found in this first pass; API remains unverified. |

## Limitations

- The registry is conservative and includes `RESEARCH_REQUIRED` for platforms where a suitable public API/MCP/CLI was not verified.
- A vendor website or documentation page is not evidence of an authenticated CK-NEXUS connection.
- Free-tier labels marked `VERIFY_*` are intentionally unresolved until current official billing/quota pages are checked.
- Further research is required for every remaining platform, particularly Thai services and newer AI builders whose product names/domains may be ambiguous.
