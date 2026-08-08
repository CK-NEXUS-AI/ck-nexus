# CK-NEXUS Creator Edition — Build Brief

## Confirmed direction

- Commercial model: one-time source-code sale.
- First customer: individual creators.
- Target window: fast MVP in 4–6 weeks.
- Interaction: menu/button driven with short creative briefs.
- Preferred backend: Python and OpenAI.
- Existing evidence: a partial SaaS Billing module; it is not a complete product.
- Product name selected in OpenAI Platform: CK-NEXUS Creator Edition.

## Product contract for v0.1.0

- A buyer can install the product locally with Python 3.11+.
- A buyer can open a Thai responsive web UI and select one of four creator agents.
- A buyer can provide a brief, audience, platform, tone, and language.
- Demo Mode returns a deterministic sample without an API key.
- Live Mode uses the OpenAI Agents SDK through `OPENAI_API_KEY`.
- Runs and agent conversation state persist in local SQLite.
- No action publishes content automatically; external side effects are outside this release.

## Inputs and outputs

- Input: `RunRequest` JSON or the equivalent web form.
- Output: Markdown content plus run metadata and a durable run ID.
- Errors: stable HTTP status plus safe error code; provider internals and secrets are not exposed.

## Approval and safety boundaries

- The product never receives a key from the browser UI.
- Destructive history deletion requires an explicit DELETE request.
- Content is generated as a draft; factual claims still require human review.
- Remote deployment should enable the bearer access token and HTTPS.

## Inferences

- A local-first BYOK product is the shortest path to a sellable source edition.
- SaaS billing, marketplace, distributed clusters, and enterprise governance are not on the v0.1.0 critical path.
- Direct menu selection is cheaper and more predictable than automatic handoffs for the first release.

## Open decisions

- Seller legal name, address, governing law, price, installations, and support period. `[ต้องการข้อมูลเพิ่ม]`
- Whether a customer receives a perpetual non-transferable license or full copyright assignment. `[ต้องการข้อมูลเพิ่ม]`
- Final default OpenAI model after live cost/quality evaluation. `[ต้องการข้อมูลเพิ่ม]`
- Production host/domain and backup retention period. `[ต้องการข้อมูลเพิ่ม]`

## Standalone build prompt

Build a local-first Python web application called CK-NEXUS Creator Edition. It must use menu-selected specialist agents, the OpenAI Agents SDK, SQLite session memory and run history, a polished Thai responsive UI, Demo Mode, BYOK Live Mode, safe error handling, optional bearer access control, request/rate limits, tests, Docker packaging, release checks, and commercial-delivery documentation. Keep the legacy SaaS Billing module optional and outside the main execution path. Never store or expose plaintext API keys.

