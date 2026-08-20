# CK-NEXUS Universal Model Capability Fabric V1

Status: Post-P0 development only. This component is not Q10/Q11/Q12 evidence and
cannot authorize Production Ready, deployment, release promotion, or PR #14 merge.

## Purpose

Extend the existing `creator_app.ai_gateway` instead of creating a second model
router. The gateway remains provider-agnostic and CK-NEXUS remains authority for
policy, privacy, credentials, execution and evidence.

The fabric now separates four different states:

1. **Declared** — provider capability appears in the reviewed global catalog.
2. **Registered** — a runtime adapter is registered in the gateway.
3. **Available** — runtime discovery returns at least one healthy model.
4. **Executable** — the selected runtime model advertises every requested capability
   and satisfies privacy/cost/context/streaming policy.

Declared capability metadata is never promoted automatically to runtime capability.

## Capability taxonomy

The existing `ModelCapability` contract has been extended to cover reasoning,
thinking, code/review/FIM, vision/image generation, audio/STT/TTS/realtime voice,
video/video generation, document AI/OCR, embeddings, multimodal embeddings,
reranking, multimodal retrieval, tool use/search, computer use, code execution,
deep research, formal proof, agentic workflows, structured output, long context,
context caching/compaction, multimodal safety, realtime social intelligence and
local execution.

## Provider declaration overlay

`catalog.py` contains reviewed capability declarations for 16 provider/vendor/runtime
families including OpenAI, Anthropic, Google AI, xAI, Mistral, Alibaba/Qwen,
DeepSeek, Amazon Nova, Cohere, NVIDIA, Meta/Llama, Groq, Moonshot/Kimi, Zhipu/GLM,
OpenRouter and Ollama.

This is a capability overlay, not a credential or endpoint registry. It must not
replace the canonical CredentialBroker, provider runtime adapter discovery or
provider connection lifecycle.

Every declaration is forced to:

```text
classification=DECLARED_ONLY
production_evidence=false
```

## Runtime metadata

`ModelDescriptor` can now carry optional runtime-discovered metadata:

- context window
- streaming support
- modalities
- languages
- free-tier signal
- open-weight signal
- metadata source

Unknown metadata remains unknown. Requests that explicitly require context size,
streaming or free-tier status fail closed when that metadata is absent.

## Routing policy

`GatewayRequest` supports:

- required model capabilities
- privacy/data class
- external-provider approval
- provider allow/deny sets
- maximum cost tier
- minimum context window
- required streaming
- required free tier
- local preference
- open-weight preference

No raw API key is carried in the request, route result or route evidence.

## Evidence boundary

`CapabilityInventory` reconciles the declaration catalog with runtime discovery and
preserves `DISCOVERED != REGISTERED != AVAILABLE`. Route evidence remains
development evidence and explicitly records `production_evidence=false`.

Provider failover, circuit breaking, credential leases and execution governance
remain responsibilities of the canonical CK-NEXUS runtime layers rather than being
reimplemented here.
