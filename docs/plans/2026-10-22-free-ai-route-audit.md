# CK-NEXUS Free AI Route and Cost-Safety Audit

Audit date: 2026-10-22
Target: `/root/ck-nexus` on VPS `vps3680569`
Method: read-only inventory/auth metadata and source review. No model inference or billable API request was made as part of this audit.

## Executive decision

**Do not currently enable unattended model calls under a claim of guaranteed free usage.** There is a configured Model Studio/DashScope credential in `/etc/cknexus/qwen.env`, and prior project evidence reports a successful Qwen inference through MCP, but neither proves the account has a zero-cost entitlement. The API route must be considered potentially billable until the console confirms a free quota/budget or a hard spending limit is configured.

## Live findings

- Repository confirmed at `/root/ck-nexus`, branch `main`.
- Root filesystem: 39 GB total, about 36 GB used, 3.9 GB available (91% used).
- Installed CLI binaries: Codex (`0.162.1`), Gemini CLI (`0.63.0`), Claude Code (`2.1.296`), OpenCode (`1.18.35`). `ollama` is not installed; no `openclaw` binary was found on this VPS PATH.
- `codex login status`: logged in using an API key (output redacted; credential exists at `/root/.codex/auth.json`). This is not proof of free usage and may incur API billing.
- `claude auth status`: `loggedIn=true`, `authMethod=oauth_token`, `apiProvider=firstParty`. The subscribed plan/remaining quota/free entitlement was not established, so do not classify it as zero-cost.
- `opencode auth list`: 0 credentials.
- No Gemini OAuth credential file was found in the standard paths checked, and no `GEMINI_API_KEY`/`GOOGLE_API_KEY` was present in the root shell. CLI installation alone does not prove authentication or free quota.
- `/etc/cknexus/qwen.env` exists with `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, and `QWEN_MODEL` set. Secret values were not read or displayed. MCP service reads this environment file, runs as `cknexus-agent`, is `active`, and listens on `127.0.0.1:8765`.
- `cknexus-mcp.service`, `cknexus-api-gateway.service`, `cknexus-scanner.service`, and `cknexus-watchdog.timer` all reported `active` at audit time.
- None of the candidate free-provider API-key environment variables were set in the inspected root shell. This does not inspect all service environments; it is not evidence that keys are absent everywhere.
- The targeted pytest check could not run: the specified test path was wrong for this repo layout and system Python has no pytest module. No tests are claimed as passed by this audit.

## Critical code finding

`creator_app/credentials/free_providers.py` assigns `free=True` by default to every entry in `AUTO_DISCOVER_PROVIDERS`, including DeepSeek, Together, Qwen/DashScope, OpenAI, Mistral, Groq, Cerebras, SambaNova, OpenRouter, Zhipu, Gemini, and Moonshot. Several are paid API routes or have conditional/free-tier availability. A static boolean in the registry is therefore not reliable evidence of zero cost. In particular, the registry's OpenAI/DeepSeek/Together/Qwen entries must not be treated as guaranteed free. `LlmKeyPool.from_environment()` also allows `CKNEXUS_LLM_KEYS` to override the provider metadata, and `acquire()` selects any configured key without enforcing a zero-cost policy at selection time.

**Safety recommendation:** fail closed by default. A route is eligible for unattended work only if it has an explicit `cost_class=local|verified_free|subscription_included|billable|unknown`, a policy source and expiry, and a budget guard. Treat `unknown` as blocked. A model's `:free` suffix or a provider's free tier must be re-verified because terms, availability, and limits change.

## Ranked routes for zero-unexpected-cost operation

1. **Local inference (best cost predictability, currently unavailable):** no Ollama binary detected and no local model server verified. Reassess only if hardware/disk capacity and an open model are suitable. Installation is not recommended yet with disk at 91%.
2. **Explicitly verified provider free tier (potential future primary):** configure a provider only after confirming account free quota, model eligibility, rate limits, terms, and spend controls in its official console. Currently no matching API-key variables were present in the inspected root shell; availability in other service environments remains unknown.
3. **Subscription-included CLI route (conditional, not proven free):** Claude Code OAuth is authenticated, but plan/usage allowance is unknown. Codex uses an API key and should be treated as potentially billable. Do not run unattended until account billing/quota policy is confirmed and hard limits are available.
4. **OpenRouter `:free` model (conditional):** code registry has a free-model slug, but no OpenRouter key was present in the inspected shell and no live free-route test was performed. Must verify the exact model, account limits, fallback behavior, and prevent silent fallback to paid models.
5. **Model Studio/DashScope Qwen (available, cost unknown / potentially billable):** service credential is configured and previous evidence reports live inference, but no zero-cost entitlement was verified. Disable unattended calls until a console budget/zero-cost quota is confirmed; never rotate keys or print them as part of this audit.
6. **OpenCode (not ready):** no credentials in the inspected auth list; no model call should be attempted.
7. **Gemini CLI (not verified):** installed but no standard OAuth credential file or API key found in checked paths. No call was attempted.

## Provider cost policy required before 24/7

- Default deny for `unknown` and `billable` routes in unattended mode.
- Separate limits for model tokens/calls, external API cost, and privileged actions; the user's 20/day limit is an internal privileged-operation cap, not an API quota or cost cap.
- Do not treat 401/402/403 or quota exhaustion as a reason to switch to a paid provider. Fail closed or use a verified zero-cost route only.
- No automatic fallback from a free model to a paid model; exact model IDs must be allowlisted.
- Set per-run timeout, retries, daily request ceiling, concurrency cap, circuit breaker, and a global kill switch.
- Record provider/model, cost class, policy version, request count, and usage evidence without logging prompts or credentials unnecessarily.
- If pricing/quota metadata is stale or cannot be fetched, stop model calls and continue with non-model tasks such as local tests, lint, queue housekeeping, and reports.

## Recommended next engineering steps

1. Patch provider metadata so paid/unknown routes are not marked `free=True` by default.
2. Add a fail-closed `CostPolicy`/`ProviderEligibility` gate before `LlmKeyPool.acquire()` and before any provider fallback.
3. Add tests proving billable/unknown routes are rejected in unattended mode, including custom `CKNEXUS_LLM_KEYS` configurations and fallback paths.
4. Verify exact Gemini/Claude/Codex account quota and Model Studio billing status through official dashboards without exposing secrets. Do not run inference for this check.
5. Only then run a minimal canary through a route explicitly classified as zero-cost, with a low daily ceiling and logs proving the exact provider/model.
6. Conduct a 24-hour soak test only after the policy gate and hard budget limits are verified.

## Evidence limits

This was a read-only audit of the connected VPS and repo. No paid API call, credential rotation, OAuth grant, new service installation, or production configuration change was performed. Provider free-tier status and account billing remain unverified unless explicitly stated above.

## Implementation update — free-only fail-closed policy

Applied on 2026-10-22 after the audit:

- `creator_app/credentials/free_providers.py`: hosted candidates now default to `free=False`; the metadata no longer claims a free tier is an unlimited zero-cost entitlement.
- `creator_app/credentials/llm_keypool.py`: unattended acquisition rejects every non-loopback endpoint, even if custom configuration marks it `free=True`. This prevents cloud fallback through `CKNEXUS_LLM_KEYS` from bypassing the policy. Local loopback endpoints remain eligible if configured.
- `creator_app/free_providers.py`: hosted free-tier adapters are disabled by default. They can only be built for a separately approved, quota-bounded development workflow via explicit `allow_limited_free_tier=True`; production `build_full_provider_router()` uses the default-disabled behavior.
- `creator_app/config.py`: cloud provider routing defaults to disabled unless `CKNEXUS_PROVIDER_ALLOW_CLOUD=true` is explicitly set. Do not set it in unattended zero-cost mode.
- Added regression tests for rejecting cloud endpoints mislabeled free, allowing loopback endpoints, not claiming hosted providers are unlimited-free, disabling hosted adapters by default, and default-denying cloud routing.

Focused verification: 83 tests passed across AutoReplyPlugin, configuration, free-provider adapters, provider routing/adapters, and credential tests. The full repository suite then passed: **753 passed, 2 skipped, 1 warning in 46.04s**. The existing R7 API contract test was updated to assert the new zero-cost default (cloud provider not preferred unless explicitly enabled). Ruff passed for all changed Python files; `git diff --check` passed.

### Live runtime safety gate

The deployed services use `/opt/cknexus-mcp` and `/usr/local/libexec/cknexus_api_gateway.py`, not the source repo directly. Their systemd drop-ins now include `UnsetEnvironment=` for DashScope/Model Studio API-key variables, leaving the protected `/etc/cknexus/qwen.env` file unchanged while withholding the credential from the running processes.

- `cknexus-mcp.service`: active after restart; live process no longer has `DASHSCOPE_API_KEY`.
- `cknexus-api-gateway.service`: active after restart; live process no longer has `DASHSCOPE_API_KEY`.
- Gateway `/v1/status` reported `upstream_integrations: not_configured` and `qwen.configured: false`.
- Gateway `/v1/qwen/health` returned HTTP 503 with `configured: false`; it did not issue the prior model health inference.
- The loopback MCP service remains on `127.0.0.1:8765`.

This intentionally disables hosted Qwen calls because the account's zero-cost/unlimited entitlement was not verified. No free unlimited inference route is currently available: Ollama/local inference is not installed, and the VPS has only 1 vCPU, about 1.9 GiB RAM (about 741 MiB available at inspection), and about 3.9 GiB free disk. Do not install a model on this host without a capacity plan. Non-LLM tasks (tests, local code analysis, queue/state housekeeping, reports) can continue without provider API spend.

Systemd drop-ins added:
- `/etc/systemd/system/cknexus-mcp.service.d/20-free-only.conf`
- `/etc/systemd/system/cknexus-api-gateway.service.d/20-free-only.conf`

The change is reversible by removing those two drop-ins and reloading systemd, but that would re-enable the unverified hosted route and should only happen after explicit cost/entitlement verification.
