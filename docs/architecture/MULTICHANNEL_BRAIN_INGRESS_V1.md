# CK-NEXUS Multi-Channel Brain Ingress v1

**Status:** IMPLEMENTED CONTRACT / ADAPTERS NOT CONNECTED / NOT PRODUCTION-READY

## Objective
Provide one provider-neutral ingress contract for Telegram, Discord, Slack, Web UI and MCP.
Adapters translate provider events into ChannelEnvelope; CK-NEXUS resolves external identity
to a local principal before exposing a request to Brain planning.

## Data path
1. Adapter validates the provider webhook signature or authenticated session.
2. Adapter normalizes the event with normalize_envelope.
3. authorize_ingress checks channel allowlist and exact, unique, enabled identity binding.
4. Accepted requests are handed to Brain as planning requests only.
5. Control Plane policy separately decides whether any task may be dispatched.
6. Tool writes, account changes, deployments and destructive operations remain governed by
   CK-NEXUS Core/L3 and existing one-time grants.

    Telegram / Discord / Slack / Web UI / MCP
                       |
                 Channel adapters
                       |
               ChannelEnvelope v1
                       |
            Identity + channel policy
                  /          \
                DENY        ACCEPT
                              |
                       Brain plan only
                              |
                     Control Plane gates
                              |
                 approved worker / evidence

## Security invariants
- Channel membership, webhook reachability and bot-admin status are not CK-NEXUS authority.
- Unbound, duplicate or disabled identity mappings fail closed.
- Channel ingress never grants tool execution, external mutation or production deployment.
- Provider credentials remain in the existing Credential Broker; never in an envelope.
- Event fingerprints support a later durable idempotency store; this v1 does not claim replay
  protection until that store and provider signature verification are integrated.
- Attachments are references only; adapters must separately validate MIME type, size, rights
  and malware status before ingestion.
- User content is untrusted input and must not override system policy or tool authorization.

## Provider routing and speed
Use the existing AIGateway / ProviderRouter for model selection. Route by capability,
data classification, latency and cost tier. Keep sensitive/personal data local unless an
explicit policy allows external processing. Add measured cache and latency telemetry before
changing routing defaults.

## AirLLM assessment
AirLLM is a candidate for low-VRAM, disk-streamed inference, not a drop-in latency accelerator.
Layer-wise loading trades peak VRAM for repeated disk-to-device transfers; full model storage,
host RAM, KV cache and token latency still matter. The current VPS has no verified NVIDIA GPU,
about 1.9 GiB RAM and 6.1 GB free root disk at the assessment snapshot. Do not install or cache
large checkpoints there. First benchmark on a separate GPU worker against a small quantized
model and hosted API using time-to-first-token, decode tokens/sec, peak RAM/VRAM, disk footprint,
concurrency and cost per successful task.

## Cloud worker direction
Use GitHub Actions hosted runners or a dedicated cloud worker for CPU/GPU-heavy jobs. Send a
typed, signed job envelope containing task ID, source commit, bounded inputs, policy class,
timeout and expected outputs. Return immutable artifacts, test logs and hashes. VPS holds no
broad cloud credentials; worker has no CK-NEXUS L3 authority. Brain validates evidence before
recording a result. A worker result is not a Q10 attestation.

## Rollout
- v1: normalized ingress contract and fail-closed identity mapping (this change).
- v1.1: Telegram/Slack/Discord adapters with signature verification and durable replay ledger.
- v1.2: channel-to-Brain planning bridge and read-only status/approval notifications.
- v2: cloud worker dispatch and artifact/evidence return with per-job credentials.
- Production remains NO-GO until the existing independent gates are met.
