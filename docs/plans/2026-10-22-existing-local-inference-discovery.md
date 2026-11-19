# CK-NEXUS Existing Local Inference Discovery

Date: 2026-10-22
Target: connected Desktop Commander devices and configured CK-NEXUS runtime endpoints
Policy: discovery-only. No model installation/download, no inference request, no cloud API request, no credentials printed.

## Scope and method

- Enumerated currently registered Desktop Commander devices.
- On each online device, checked known local inference binaries, relevant processes/services, standard inference TCP ports, and common existing model-cache directories.
- On the VPS, checked running Docker container names/images/port mappings, local listener inventory, known CK-NEXUS API services, Tailscale peer inventory, SSH host aliases, and repository configuration references for existing remote inference hosts.
- Sent only local GET requests to health/model-list paths on localhost for service identification; did not send prompt/completion requests. No external hosts or broad LAN ranges were scanned.

## Connected devices

1. `vps3680569.trouble-free.net` — online.
2. `localhost` (Termux device) — online.

No other Desktop Commander device was registered/online in the account inventory at the time of inspection. Tailscale status on the VPS reported no peer entries; no additional peer machines were therefore probed.

## Findings

### VPS

- No `ollama`, `llama-server`, `llama-cli`, `vllm`, `local-ai`, `lmstudio`, `llamafile`, `koboldcpp`, or `text-generation-launcher` command found on PATH.
- No matching model-serving systemd unit or Docker container identified in the service/container inventory.
- No inference listener identified on standard local ports 11434, 8000, 1234, or 8080. Listeners on 8765, 8790, and other ports belong to CK-NEXUS/MCP/scanner or unrelated services, not a verified model server.
- No known local model files/cache found in the checked common directories. Search did find old Qwen evidence logs; these are historical Cloud API evidence, not local model weights.
- Docker Assistant `http://127.0.0.1:8088/health` returned HTTP 200 with `ai_provider_configured: false`. This is a healthy assistant service but it is not currently connected to an AI provider.
- CK-NEXUS API Gateway and MCP remain separate operational services. Qwen provider access remains disabled by the existing free-only safety gate; no inference call was made.
- Resource snapshot: 1 vCPU, about 1.9 GiB RAM with about 689 MiB available, and about 3.9 GiB disk free (filesystem around 91% used). Installing a local model on this VPS is not recommended without a capacity/storage plan.

### Termux device

- No known local inference binary or matching model-serving process found.
- No listener found on standard model ports checked.
- Local checks to `127.0.0.1:11434/api/tags`, `127.0.0.1:8000/v1/models`, `127.0.0.1:1234/v1/models`, and `127.0.0.1:8080/health` were unreachable.
- No model weights/cache found in the common Termux model directories checked.

### Existing remote endpoint references

- Repository configuration contains example references for localhost inference (for example `OLLAMA_BASE_URL=http://127.0.0.1:11434`), but no verified non-local inference host was discovered in the inspected configuration.
- Root SSH config exposes only a wildcard entry and the known VPS address; no additional configured SSH alias was found.
- Tailscale has an active interface on the VPS but no peers were listed, so there was no additional reachable Tailscale model host to inspect.

## Decision

**No already-installed Local Model or Inference Server was found ready for CK-NEXUS to use on the connected devices inspected.** Do not enable hosted provider calls as a substitute: no guaranteed unlimited zero-cost entitlement has been established. Keep the free-only fail-closed gate active.

## Next safe actions

1. If another workstation/server already runs Ollama, llama.cpp, LM Studio, vLLM, or an OpenAI-compatible endpoint, register/connect that device through an approved secure route (prefer private VPN and loopback-bound service behind authenticated tunnel); then inspect only that explicitly authorized host.
2. Do not expose model-server ports publicly and do not put API keys into repository files or logs.
3. Until a local endpoint is found, continue CK-NEXUS non-LLM work (tests, lint, repository analysis, task/checkpoint bookkeeping, watchdog and audit) without provider calls.


## Follow-up C — Existing coding CLIs and AI-connected services

Date: 2026-10-22. Discovery-only; no inference/completion requests and no billing API calls.

### VPS coding CLI metadata

- Codex CLI present, version `0.162.1`; `codex login status` reports logged in using an API key. This is **not** evidence of free usage; treat as potentially billable and do not use for unattended tasks without verified billing controls.
- Claude Code present, version `2.1.296`; `claude auth status` reports logged in with `oauth_token` and `firstParty` provider. Account plan and remaining included quota were not established, so this is not classified as free/unlimited.
- OpenCode present, version `1.18.35`; `opencode auth list` returned no credentials.
- Gemini CLI command was present on PATH but its version probe produced no readable version output within the bounded check. No standard Gemini OAuth credential file was found in the paths checked; no inference attempted.
- OpenClaw was not on the VPS PATH.

### Termux / OpenClaw

- OpenClaw CLI is installed (`2026.10.5`), but its bounded `gateway status` check produced no readable status output within the timeout. This is inconclusive, not proof of a healthy gateway.
- OpenClaw configuration file exists at `~/.openclaw/openclaw.json`; credential values were not read or printed. Model status/list commands were not pursued after the remote execution safety layer blocked the configuration-inspection attempt.
- No Codex, Claude, OpenCode, Ollama, or llama-server command was found on Termux PATH. Gemini CLI was present but did not produce a readable version string in the bounded probe. No model-server process/listener was identified.
- The Termux environment exposes the variable name `OPENAI_API_KEY`; its value was deliberately not read. Presence of a variable does not prove it is valid, free, or safe to call. No API request was made.

### Running CK-NEXUS services

- Docker Assistant health endpoint returned HTTP 200 but explicitly reports `ai_provider_configured: false`.
- CK-NEXUS Gateway `/v1/status` returned HTTP 200 with `upstream_integrations: not_configured`, `production_ready: false`, and `qwen.configured: false`.
- Current Docker inventory contains CK-NEXUS operational containers and Docker Assistant, but no Ollama, vLLM, LocalAI, or other identified inference-server container.
- No service was reconfigured, restarted, installed, or removed during this follow-up.

### Decision

No connected AI CLI or service was proven to provide **free, unlimited inference**. Authenticated CLI status alone does not establish subscription inclusion, rate limits, or cost. Keep the existing fail-closed cloud safety gate and do not use Codex, Claude, Gemini, OpenCode, OpenClaw, or the Termux OpenAI environment for inference until entitlement and hard spending controls are independently verified. Continue non-LLM work while these checks remain unresolved.
