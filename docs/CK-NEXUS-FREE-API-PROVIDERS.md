# CK-NEXUS Free API Provider Status

Last reviewed: 2026-11-17

## Current VPS account checks

| Provider | Credential | Read-only check | Routing decision |
|---|---|---|---|
| Google Gemini | Present in /etc/cknexus/gemini.env | GET /v1beta/models returned HTTP 200; gemini-3.8-flash listed; direct generation returned HTTP 503 during smoke test | Registered as secondary free-tier fallback; live inference currently unavailable (HTTP 503) |
| OpenRouter | Present in /etc/cknexus/openrouter.env | GET /api/v1/models returned HTTP 200; zero-price models listed | Enabled as primary with openrouter/free |
| Groq | Present in /etc/cknexus/groq.env | GET /openai/v1/models returned HTTP 403 | Not routed; key/account access needs repair |
| Alibaba Model Studio / Qwen | Present in /etc/cknexus/qwen.env | Singapore workspace /models returned HTTP 200 | Not routed as free; Singapore general free quota is not available under current published policy |
| OpenAI | Present in legacy /etc/cknexus/creator.env | Not probed; no recurring free API tier | Disabled by CKNEXUS_FREE_ONLY=true |

No API keys or key fragments are stored in this document or in Git.

## Free provider candidates to add when account keys are available

| Provider | Published no-cost allowance | Important condition | Status |
|---|---|---|---|
| Cohere Evaluation | 1,000 API calls/month; 20 requests/minute for Chat models | Evaluation key, not production entitlement | Not connected |
| Cloudflare Workers AI | 10,000 Neurons/day on Workers Free | On Workers Paid, usage above the free allocation is billable; only free-plan eligible models should be used | Not connected |
| Hugging Face Inference Providers | $0.10 monthly credits for free users, subject to change | Small monthly credit; extra usage requires a credit purchase | Not connected |
| Mistral API | Free experimentation access may be available by account | Verify current account limits before routing | Not verified |
| SambaNova / NVIDIA NIM / Cerebras | Free or trial offers vary by account and date | Do not classify as recurring free without checking account terms | Not verified |

## Routing controls

- CKNEXUS_FREE_ONLY=true prevents paid OpenAI from being registered as a fallback.
- CKNEXUS_ENABLE_OPENROUTER_FREE=true enables OpenRouter's zero-price model router.
- CKNEXUS_OPENROUTER_MODEL=openrouter/free delegates free-model selection to OpenRouter.
- CKNEXUS_GEMINI_MODEL=gemini-3.8-flash selects a model listed in the Gemini free-tier catalog as the secondary provider.
- No provider is considered live-inference verified by a /models response alone.
- No live generation request was sent during setup, so no inference quota was consumed by this integration work.

## Official terms

- Gemini pricing and free-tier data use: https://ai.google.dev/gemini-api/docs/pricing
- OpenRouter free models and limits: https://openrouter.ai/collections/free-models
- Cohere evaluation keys and rate limits: https://docs.cohere.com/docs/rate-limits
- Cloudflare Workers AI free allocation and overage: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Hugging Face Inference Provider credits: https://huggingface.co/docs/inference-providers/pricing
- Alibaba Model Studio free quota and regional restrictions: https://help.aliyun.com/en/model-studio/new-free-quota
