# CK-NEXUS Remote AI and Worker Architecture Research — 2026-11-01

## Executive decision

Use the VPS as the control plane, not the heavy compute plane. Keep CK-NEXUS Core as the sole authority for policy, memory, credentials, evidence and promotion. Move repeatable validation to GitHub-hosted runners. Route inference to managed endpoints only when provider health, latency, privacy, quota and cost policies permit. Keep large document parsing and visual processing in separate workers.

## Source-backed patterns

### 1. GitHub MCP and cloud agent

GitHub documents MCP as a standard connector for context and tools across Copilot surfaces. It recommends selecting only needed tools and keeping credentials scoped to required resources. Its cloud agent runs in a cloud environment with default read-only GitHub access and Playwright limited to its own environment. This supports a CK-NEXUS design where the VPS sends a fixed task to a remote worker and receives a result, rather than exposing local SSH or root access.

Source: https://docs.github.com/en/copilot/concepts/customizations/mcp

### 2. DigitalOcean Action Gateway

DigitalOcean's managed Action Gateway connects agents to GitHub, Linear and custom MCP providers. It handles tool discovery, credentials, permission policies and execution. Its catalog is intentionally accessed through meta-tools action_search, action_invoke and action_code rather than loading every tool schema into the model context. Sessions can allow reads and require approval for updates.

Adoption decision: useful architectural pattern for reducing context and credential exposure; do not assume account availability, pricing, or free usage. Do not make it a second CK-NEXUS authority plane.

Source: https://docs.digitalocean.com/products/managed-agents/action-gateway/concepts/overview/

### 3. AWS Agent Toolkit

AWS publishes an official toolkit combining a managed AWS MCP server, curated skills, plugins and rules. The MCP server exposes AWS service tools and documentation; skill packages load task-specific instructions on demand. IAM, CloudTrail and CloudWatch are part of the operational guardrail model.

Adoption decision: use selected skills and narrow IAM roles only if CK-NEXUS later operates AWS resources. Do not install the whole toolkit on the VPS or grant root account authority.

Sources:
- https://github.com/aws/agent-toolkit-for-aws
- https://docs.aws.amazon.com/agent-toolkit/latest/userguide/

### 4. Hugging Face Inference Endpoints

Inference Endpoints support autoscaling and scale-to-zero. Scaling to zero reduces idle compute but introduces cold-start delays; the proxy can return 503 while the replica initializes. The service supports explicit replica ceilings and scaling schedules.

Adoption decision: a candidate for burst inference and embeddings, behind Provider Router and a bounded queue. Use timeouts, retry budgets, maximum replicas, budget limits and a cold-start aware queue. No account, endpoint, cost or inference is currently verified.

Source: https://huggingface.co/docs/inference-endpoints/guides/autoscaling

### 5. Cloudflare Workers AI

Workers AI offers managed text generation, embeddings, image-to-text and other tasks. Its documentation publishes rate limits by task type and model, and paid models may have different limits.

Adoption decision: candidate for short-lived inference, embeddings and visual metadata extraction. Require model-level quota/cost controls and provider-specific privacy review before activation.

Source: https://developers.cloudflare.com/workers-ai/platform/limits/

### 6. AirLLM

AirLLM's maintainer documents layer-wise model streaming: only the current transformer layer or selected experts are loaded to GPU, while the remaining weights stay on disk. The README reports very low VRAM for large models, including 70B on approximately 4GB. The technique trades GPU memory for repeated disk I/O and storage capacity.

Independent technical reviews emphasize that low VRAM is not the same as useful token throughput; per-token disk reads can dominate latency and the headline results need hardware-specific benchmarking.

Adoption decision: research-only. Do not install on the 1.9 GiB RAM / 6 GiB free disk VPS. Benchmark only on a separate machine with fast NVMe, enough disk and measured time-to-first-token/tokens-per-second.

Sources:
- https://github.com/lyogavin/airllm
- https://huggingface.co/blog/lyogavin/airllm
- https://wavect.io/blog/airllm-layer-wise-inference-low-vram/

### 7. Pinterest API and MCP

Pinterest API v5 supports reading Pins and Boards with OAuth scopes boards:read and pins:read. List endpoints paginate using a bookmark and support up to 250 items per page. Pinterest's official MCP announcement describes search, board exploration and insights, but its current page asks developers to sign up for launch updates; it is not treated as generally available.

Adoption decision: implement API v5 read-only connector first. Store Pin IDs, board IDs, title, description, alt text, source URL and image URL only. Do not download/rehost images, infer reuse rights, train models on them, or enable write scopes. Require an app token with only the two read scopes.

Sources:
- https://developers.pinterest.com/docs/api/v5/pins-list/
- https://developers.pinterest.com/docs/reference/pagination/
- https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- https://developers.pinterest.com/about-pinterest-mcp/

## CK-NEXUS implementation choices in this branch

1. Add a fixed GitHub Actions Cloud Worker. Only tests, security, and full_validation task profiles are accepted.
2. Dispatch requires an immutable 40-character subject SHA. The runner checks out that exact SHA and verifies identity before execution.
3. Runner permissions are read-only; checkout credentials are not persisted; no arbitrary shell, arbitrary repository, branch, URL or environment map is accepted.
4. Validation artifacts include request ID, source SHA/tree, GitHub run ID and task outcomes. They are candidate evidence only, not Q10 or release evidence.
5. The runtime adapter uses the existing GitHub App and Credential Broker. Cloud dispatch remains disabled by default until the narrow Actions permission is confirmed.
6. Add Pinterest API v5 read-only adapter and a SQLite reference catalogue. Collection supports up to 500 references across up to 25 public boards, with 250 pins per API page. Image bytes are not downloaded.
7. Add AWS Agent Toolkit, DigitalOcean Action Gateway, Hugging Face Inference Endpoints, Cloudflare Workers AI, AirLLM and Pinterest MCP to the typed capability catalog as discovery-only candidates until account, cost, license, permission and live execution gates pass.

## Pinterest source audit result

The user-supplied short URL resolves to Pin 1085578685222677540, titled “What Is AirLLM? Run 70B AI Models on 4GB GPUs”, on the public SPAUL Hub board (1085578753870547641). The board reports 6 Pins. The Pin page exposes 5 board thumbnail URLs and one detailed image URL. Pinterest search pages returned a login shell without authentication.

Current result: 1 detailed Pin record + 5 thumbnail URLs = 5 unique image assets; 495 short of the requested 500. This is not represented as a completed 500-image collection. The collector is ready for an authorized Pinterest API token and additional public board IDs.

The Pin points to https://spaulhub.com/blogs/airllm-70b-on-4gb-gpu-layer-wise-inference/. The AirLLM technique is worth studying for low-VRAM offload, but not for VPS installation: the VPS has no suitable GPU and limited free disk, and the inference method can be storage-bound.

## Deployment and verification boundaries

- No third-party Pinterest image bytes were downloaded or rehosted.
- No Pinterest token is present in source code or chat.
- Pinterest API collection is inactive until a read-only token is placed in the Credential Broker environment binding.
- No AirLLM, Docling, RAGFlow or vector database was installed on the VPS.
- No provider account or paid endpoint was created.
- Cloud worker is disabled by default.
- No Q10/Q11/Q12 evidence or Production status was modified.
