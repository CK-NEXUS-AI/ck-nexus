# CK-NEXUS Chat Portal — Development Notes

## Scope

This branch contains a static chat workspace for the existing CK-NEXUS Creator API. It reuses the existing Development Council endpoints:

- GET /api/status
- GET /api/dev-team
- GET /api/agnes/status
- POST /api/chat (authenticated chat façade)

The UI does not call provider APIs directly and does not contain provider credentials. The access token is entered by the operator and held in browser sessionStorage only. The chat session ID is generated per new conversation. The response is rendered as text, not HTML.

## Browser/API connection

The page is published under GitHub Pages origin:

https://ck-nexus-ai.github.io

The API must have its own approved HTTPS origin and reverse-proxy route. Do not expose loopback services 127.0.0.1:8000 or 127.0.0.1:8790 directly to the public internet.

When the API is intentionally made reachable through an authenticated HTTPS ingress, configure the Creator service environment with an explicit origin:

CKNEXUS_CHAT_ALLOWED_ORIGINS=https://ck-nexus-ai.github.io

Multiple origins are comma-separated. Wildcards, credentials, URL paths, query strings, and non-local HTTP origins are rejected. CORS credentials are disabled. Browser requests use credentials: omit and send the CK-NEXUS bearer token in the Authorization header.

## Current backend contract

POST /api/chat requires a configured server-side access token, validates the request through CK-NEXUS authentication and the run rate limiter, obtains an Agnes read-only skill plan, and then calls the Development Council provider. The response reports selected skills and approval requirements but always sets execution_status=NOT_EXECUTED. No Agnes skill is executed by the chat route. The Development Council is advisory-only; it does not grant execution, approval, merge, deployment, or production authority.

The Creator API can use the configured Gemini text adapter as a single-model fallback when the OpenAI Agents SDK provider is unavailable. In this mode, chat is advisory-only and explicitly reports GEMINI_SINGLE_MODEL_FALLBACK. It does not call five independent advisers, does not perform live web search, and does not execute tools. Debate mode is blocked because a single model is not an independent multi-agent debate. Gemini usage consumes the configured provider quota; no provider call is made during automated tests.

The current observed VPS service reports mode=gemini, model=gemini-2.5-flash, key_configured=true, and dev_team_ready=false before this branch's fallback change is deployed. After deployment, the expected API status is a Gemini single-model fallback, subject to the live provider configuration and CORS ingress. A working API connection is not equivalent to a multi-agent Council being ready.

The n8n API was not accessible through the current local read-only request (HTTP 401). The exported CK-NEXUS AI Brain workflow found in historical evidence is not proof of the current active workflow state. The page deliberately displays n8n as NOT VERIFIED.

## Security and operating rules

- No provider key or n8n credential in HTML, JavaScript, GitHub Pages, or browser storage.
- No arbitrary URL proxy, shell execution, file write, email send, GitHub mutation, or deployment operation from the chat page.
- Treat user content and tool output as untrusted.
- Keep agent execution behind CK-NEXUS policy and approval paths.
- Do not claim streaming: the current Development Council endpoint returns a completed JSON response.
- Do not claim production readiness from a successful UI/API smoke test.

## Deployment is not performed by this change

This branch has not been pushed, merged, or deployed. The running VPS Creator service and API Gateway were not restarted or modified. The public GitHub Pages site still serves the last published commit until an approved push updates the Pages source.
