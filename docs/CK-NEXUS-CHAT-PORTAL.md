# CK-NEXUS Chat Portal — Deployment Notes

## Scope

The static chat workspace connects to the existing CK-NEXUS Creator API. The browser calls only these scoped endpoints:

- GET /api/chat/status
- POST /api/chat

The page does not call provider APIs directly and does not contain provider credentials. A dedicated Chat Access Token is entered by the operator and held in browser sessionStorage for the current tab only. It is not the global CK-NEXUS API token and cannot authorize other Creator API routes. The chat session ID is generated per new conversation. Responses are rendered as text, not HTML.

## Browser/API connection

The GitHub Pages origin is https://ck-nexus-ai.github.io. The API must have its own approved HTTPS origin and an authenticated ingress. Do not expose loopback services directly to the public internet.

Configure the Creator service with:

- CKNEXUS_CHAT_ALLOWED_ORIGINS=https://ck-nexus-ai.github.io
- CKNEXUS_CHAT_ACCESS_TOKEN=<dedicated-random-chat-secret>

Keep CKNEXUS_ACCESS_TOKEN separate for the full Creator API. Never reuse it in the public browser. Multiple CORS origins are comma-separated. Wildcards, credentials, URL paths, query strings, and non-local HTTP origins are rejected. CORS credentials are disabled. Browser requests use credentials: omit and send the dedicated Chat token in the Authorization header.

GET /api/chat/status returns only the chat readiness, provider/model, chat mode, and whether Agnes read-only planning is enabled. POST /api/chat requires the same dedicated Chat token and the existing run rate limiter. The token does not authorize /api/dev-team, /api/agnes/*, /api/runs, connectors, integrations, or other protected routes.

## Runtime behavior

The chat route obtains an Agnes read-only skill plan and then calls the Development Council provider. It reports selected skills and approval requirements but always sets execution_status=NOT_EXECUTED and authority_effect=NONE. No Agnes skill is executed by the chat route. The Development Council is advisory-only; it does not grant execution, approval, merge, deployment, or production authority.

The configured Gemini adapter can provide a single-model fallback when the OpenAI Agents SDK provider is unavailable. In this mode, chat explicitly reports GEMINI_SINGLE_MODEL_FALLBACK. It does not call five independent advisers, does not perform live web search, and does not execute tools. Debate mode is blocked because one model is not an independent multi-agent debate. Gemini usage consumes the configured provider quota; automated tests do not call the live provider.

The n8n panel remains NOT VERIFIED until a current live integration check confirms its status.

## Security and operating rules

- No provider key, global CK-NEXUS API token, or n8n credential in HTML, JavaScript, GitHub Pages, or browser storage.
- No arbitrary URL proxy, shell execution, file write, email send, GitHub mutation, or deployment operation from the chat page.
- Treat user content and tool output as untrusted.
- Keep agent execution behind CK-NEXUS policy and approval paths.
- Do not claim streaming: the Development Council endpoint returns a completed JSON response.
- Do not claim production readiness from a successful UI/API smoke test.
- The public GitHub Pages frontend is public; only the API and its dedicated Chat token gate access to the chat backend.

## Deployment

The frontend is published from the repository's feat/ck-nexus-test-portal branch /docs source. The backend runs from a commit-pinned release directory with the existing CK-NEXUS data root retained.

The public ingress is a separate loopback proxy on port 8102. It forwards only GET /api/chat/status and POST /api/chat to the Creator API on port 8000. It does not expose the other Creator API routes, does not forward cookies, limits request bodies to 64 KiB, and permits only the exact GitHub Pages HTTPS origin. Cloudflare Quick Tunnel points to this proxy, not directly to the full Creator API. The existing read-only evidence tunnel remains unchanged.

The current temporary API URL is https://executive-slowly-scores-char.trycloudflare.com and is prefilled in the Chat settings. Cloudflare Quick Tunnel assigns a temporary hostname that can change if the tunnel is recreated. A stable production URL requires a named Cloudflare Tunnel and a verified domain; do not treat the temporary URL as a production endpoint.
