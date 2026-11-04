from __future__ import annotations

from datetime import UTC, datetime

from .catalog import KnowledgeCatalog
from .models import EvidenceLevel, KnowledgeItem, KnowledgeSource, KnowledgeStatus

_DISCOVERED_AT = datetime(2026, 8, 23, tzinfo=UTC)


def _source(source_id: str, name: str, url: str, source_type: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        name=name,
        url=url,
        source_type=source_type,
        discovered_at=_DISCOVERED_AT,
        evidence_level=EvidenceLevel.DOCUMENTED,
    )


def initial_catalog() -> KnowledgeCatalog:
    items = (
        KnowledgeItem(
            item_id="memory.langgraph",
            name="LangGraph long-term memory",
            category="memory",
            summary="Namespace-backed persistent memory across agent sessions.",
            usage="Prefer as an existing store abstraction before building custom memory storage.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "langchain.long-term-memory",
                    "LangChain long-term memory",
                    "https://docs.langchain.com/oss/python/langchain/long-term-memory",
                    "official_docs",
                ),
            ),
            relevance=("AGNES memory", "user preferences", "cross-session context"),
            capabilities=("long_term_memory", "namespaced_store", "postgres_storage"),
            tags=frozenset({"memory", "agent", "reuse_first"}),
        ),
        KnowledgeItem(
            item_id="memory.mem0",
            name="Mem0",
            category="memory",
            summary="Self-hostable memory layer with entity-scoped memory and search.",
            usage="Evaluate as an adapter for user, agent, app, and run scoped memory.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "mem0.open-source",
                    "Mem0 open source overview",
                    "https://docs.mem0.ai/open-source/overview",
                    "official_docs",
                ),
                _source(
                    "mem0.entity-scope",
                    "Mem0 entity-scoped memory",
                    "https://docs.mem0.ai/platform/features/entity-scoped-memory",
                    "official_docs",
                ),
            ),
            relevance=("AGNES memory", "privacy boundaries", "multi-agent memory"),
            capabilities=("long_term_memory", "entity_scoping", "semantic_search"),
            tags=frozenset({"memory", "self_hosted", "adapter_candidate"}),
        ),
        KnowledgeItem(
            item_id="memory.letta",
            name="Letta",
            category="memory",
            summary="Open-source stateful agent runtime with persistent memory and skills.",
            usage="Study as a reference runtime before implementing stateful-agent features.",
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "letta.docs",
                    "Letta documentation",
                    "https://docs.letta.com/",
                    "official_docs",
                ),
            ),
            relevance=("AGNES stateful agents", "continual memory", "skills"),
            capabilities=("stateful_agent", "persistent_memory", "skills"),
            tags=frozenset({"memory", "agent_runtime", "reference"}),
        ),
        KnowledgeItem(
            item_id="voice.elevenlabs",
            name="ElevenLabs text to speech",
            category="voice",
            summary="Multilingual TTS with voice settings, speed control, and language handling.",
            usage="Use through a provider adapter for expressive cloud voice rendering.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "elevenlabs.tts",
                    "ElevenLabs text to speech",
                    "https://elevenlabs.io/docs/overview/capabilities/text-to-speech",
                    "official_docs",
                ),
            ),
            relevance=("AGNES voice persona", "multilingual speech", "prosody"),
            capabilities=("text_to_speech", "multilingual_voice", "voice_settings"),
            tags=frozenset({"voice", "cloud", "adapter_candidate"}),
        ),
        KnowledgeItem(
            item_id="voice.openai",
            name="OpenAI Audio speech",
            category="voice",
            summary="Hosted speech generation with instructions, speed control, and custom voices.",
            usage="Use through the existing provider adapter rather than building a speech model.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "openai.audio.speech",
                    "OpenAI Audio API speech reference",
                    "https://platform.openai.com/docs/api-reference/audio",
                    "official_docs",
                ),
            ),
            relevance=("AGNES voice persona", "prosody instructions", "provider routing"),
            capabilities=("text_to_speech", "voice_instructions", "speed_control"),
            tags=frozenset({"voice", "cloud", "adapter_candidate"}),
        ),
        KnowledgeItem(
            item_id="voice.piper",
            name="Piper text to speech",
            category="voice",
            summary="Local neural text-to-speech engine with a mature deployment history.",
            usage=(
                "Evaluate for offline and privacy-first voice fallback where voice licenses "
                "permit."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "piper.github",
                    "Piper GitHub repository",
                    "https://github.com/rhasspy/piper",
                    "source_repository",
                ),
            ),
            relevance=("AGNES offline voice", "privacy-first speech", "local inference"),
            observations=(
                "Upstream development moved; voice model licenses require separate review.",
            ),
            capabilities=("text_to_speech", "offline_voice", "local_inference"),
            tags=frozenset({"voice", "offline", "license_review_required"}),
        ),
        KnowledgeItem(
            item_id="design.wcag22",
            name="WCAG 2.2",
            category="accessibility",
            summary="W3C accessibility recommendation with testable success criteria.",
            usage="Use as the accessibility baseline for AGNES and CK-NEXUS interface design.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "w3c.wcag22",
                    "Web Content Accessibility Guidelines 2.2",
                    "https://www.w3.org/TR/WCAG22/",
                    "standard",
                ),
            ),
            relevance=("Design Intelligence", "accessibility", "verification"),
            capabilities=("accessibility_standard", "testable_criteria"),
            tags=frozenset({"design", "standard", "accessibility"}),
        ),
        KnowledgeItem(
            item_id="design.tokens.format",
            name="Design Tokens Format Module",
            category="design_system",
            summary="Community specification for interoperable design token data.",
            usage=(
                "Align Design Intelligence token serialization with the published format "
                "model."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "design-tokens.format",
                    "Design Tokens Format Module",
                    "https://www.designtokens.org/tr/drafts/format/",
                    "specification",
                ),
            ),
            relevance=("Design Tokens", "cross-tool consistency", "design system"),
            capabilities=("design_tokens", "interoperable_format"),
            tags=frozenset({"design", "tokens", "interop"}),
        ),
        KnowledgeItem(
            item_id="market.langgraph.2026",
            name="LangGraph and LangSmith 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "LangGraph provides durable state, persistence, memory and human approval; "
                "LangSmith adds production deployment and observability."
            ),
            usage=(
                "Treat LangGraph as a capable orchestration runtime. Differentiate CK-NEXUS "
                "on evidence-bound authority rather than claiming LangGraph lacks memory or HITL."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "langgraph.official",
                    "LangGraph product overview",
                    "https://www.langchain.com/langgraph",
                    "official_docs",
                ),
                _source(
                    "langsmith.deployment",
                    "LangSmith Deployment",
                    "https://www.langchain.com/langsmith/deployment",
                    "official_docs",
                ),
            ),
            relevance=("agent orchestration", "memory", "HITL", "observability"),
            observations=(
                "Do not claim LangGraph has no persistence, memory or human approval.",
                "Evidence-by-construction remains a CK-NEXUS positioning hypothesis to prove.",
            ),
            capabilities=(
                "durable_execution",
                "checkpointing",
                "long_term_memory",
                "human_in_the_loop",
                "observability",
            ),
            tags=frozenset({"market", "competitor", "agent_framework", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.crewai.2026",
            name="CrewAI 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "CrewAI documents production-ready agents and flows with memory, knowledge, "
                "guardrails, persistence, observability, HITL and enterprise RBAC."
            ),
            usage=(
                "Do not position CrewAI as demo-only. Compare execution authority, evidence "
                "identity, verifier independence and cross-tool policy enforcement instead."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "crewai.docs",
                    "CrewAI documentation",
                    "https://docs.crewai.com/",
                    "official_docs",
                ),
            ),
            relevance=("multi-agent", "flows", "guardrails", "enterprise deployment"),
            observations=(
                "Do not claim CrewAI has no memory, guardrails, observability or RBAC.",
            ),
            capabilities=(
                "multi_agent",
                "persistent_flows",
                "memory",
                "guardrails",
                "human_in_the_loop",
                "rbac",
                "observability",
            ),
            tags=frozenset({"market", "competitor", "agent_framework", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.microsoft.agent_framework.2026",
            name="Microsoft Agent Framework 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "Microsoft Agent Framework is the direct successor to AutoGen and Semantic "
                "Kernel and combines agents, workflows, memory, middleware and telemetry."
            ),
            usage=(
                "Track Microsoft Agent Framework as the current Microsoft competitor instead "
                "of treating AutoGen and Semantic Kernel as independent strategic endpoints."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "microsoft.agent-framework",
                    "Microsoft Agent Framework overview",
                    "https://learn.microsoft.com/en-us/agent-framework/overview/",
                    "official_docs",
                ),
                _source(
                    "microsoft.agent-framework.workflows",
                    "Microsoft Agent Framework workflows",
                    "https://learn.microsoft.com/en-us/agent-framework/workflows/",
                    "official_docs",
                ),
            ),
            relevance=("AutoGen", "Semantic Kernel", "workflow", "checkpoint", "HITL"),
            observations=(
                "AutoGen and Semantic Kernel remain relevant for migration and installed bases.",
                "New competitive analysis should prioritize Microsoft Agent Framework.",
            ),
            capabilities=(
                "multi_agent",
                "graph_workflow",
                "checkpointing",
                "human_in_the_loop",
                "memory",
                "middleware",
                "telemetry",
                "mcp",
            ),
            tags=frozenset({"market", "competitor", "microsoft", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.openai.agents_sdk.2026",
            name="OpenAI Agents SDK 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "OpenAI Agents SDK is production-ready and includes guardrails, persistent "
                "sessions, HITL, tracing, MCP, sandbox agents and durable integrations."
            ),
            usage=(
                "Treat OpenAI Agents SDK as an intelligence/runtime provider that CK-NEXUS can "
                "govern, not as a framework missing basic agent safety primitives."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "openai.agents-sdk",
                    "OpenAI Agents SDK",
                    "https://openai.github.io/openai-agents-python/",
                    "official_docs",
                ),
                _source(
                    "openai.agents-sdk.hitl",
                    "OpenAI Agents SDK human in the loop",
                    "https://openai.github.io/openai-agents-python/human_in_the_loop/",
                    "official_docs",
                ),
            ),
            relevance=("agent SDK", "guardrails", "sessions", "HITL", "tracing"),
            observations=(
                "Do not claim the SDK lacks approval, guardrails, persistent sessions or tracing.",
            ),
            capabilities=(
                "multi_agent",
                "guardrails",
                "persistent_sessions",
                "human_in_the_loop",
                "tracing",
                "mcp",
                "sandbox",
            ),
            tags=frozenset({"market", "provider", "agent_sdk", "adapter_candidate"}),
        ),
        KnowledgeItem(
            item_id="market.aws.agentcore.2026",
            name="Amazon Bedrock AgentCore 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "AgentCore provides runtime, gateway, memory, identity, observability and a "
                "Cedar policy engine that evaluates every governed gateway tool invocation."
            ),
            usage=(
                "Do not claim governance plus AI is unique. Differentiate CK-NEXUS on portable, "
                "provider-neutral sovereignty and exact-subject execution evidence."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "aws.agentcore.policy",
                    "Policy in Amazon Bedrock AgentCore",
                    "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/"
                    "policy-getting-started.html",
                    "official_docs",
                ),
            ),
            relevance=("enterprise governance", "policy engine", "tool authorization"),
            observations=(
                "AgentCore can enforce deny-by-default Cedar policies outside agent code.",
                "AWS ecosystem coupling creates a different deployment tradeoff than CK-NEXUS.",
            ),
            capabilities=(
                "policy_engine",
                "deny_by_default",
                "tool_authorization",
                "identity",
                "memory",
                "observability",
            ),
            tags=frozenset({"market", "competitor", "cloud", "governance", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.litellm.2026",
            name="LiteLLM 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "LiteLLM is a multi-provider gateway with authentication, authorization, "
                "virtual keys, spend controls, guardrails, retries and fallbacks."
            ),
            usage=(
                "Treat LiteLLM as a reusable gateway option or comparison point; do not call "
                "modern LLM gateways simple traffic pipes."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "litellm.docs",
                    "LiteLLM documentation",
                    "https://docs.litellm.ai/",
                    "official_docs",
                ),
            ),
            relevance=("gateway", "routing", "budget", "virtual keys", "guardrails"),
            observations=(
                "Gateway governance is substantial but does not by itself equal task evidence.",
            ),
            capabilities=(
                "model_gateway",
                "routing",
                "budget_control",
                "virtual_keys",
                "guardrails",
                "observability",
            ),
            tags=frozenset({"market", "gateway", "adapter_candidate", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.portkey.2026",
            name="Portkey 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "Portkey provides gateway routing, central guardrails, RBAC, audit logs, "
                "observability and enterprise governance controls."
            ),
            usage=(
                "Compare Portkey at the gateway governance layer. CK-NEXUS should separate "
                "administrative audit logs from proof of a verified task execution."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "portkey.guardrails",
                    "Portkey Guardrails",
                    "https://portkey.ai/docs/product/guardrails",
                    "official_docs",
                ),
                _source(
                    "portkey.access-control",
                    "Portkey Access Control Management",
                    "https://portkey.ai/docs/product/enterprise-offering/access-control-management",
                    "official_docs",
                ),
            ),
            relevance=("gateway", "RBAC", "audit", "DLP", "prompt injection"),
            observations=(
                "Do not claim gateways lack prompt-injection or data-loss controls.",
            ),
            capabilities=(
                "model_gateway",
                "guardrails",
                "rbac",
                "audit_logs",
                "observability",
                "prompt_injection_detection",
            ),
            tags=frozenset({"market", "gateway", "competitor", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.openrouter.2026",
            name="OpenRouter 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "OpenRouter provides provider routing, budgets, model/provider allowlists, ZDR, "
                "prompt-injection controls, sensitive-data filtering and BYOK."
            ),
            usage=(
                "Treat OpenRouter as a governed routing service. CK-NEXUS differentiation must "
                "extend beyond cost routing and input/output gateway policy."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "openrouter.guardrails",
                    "OpenRouter Guardrails",
                    "https://openrouter.ai/docs/guides/features/guardrails/overview",
                    "official_docs",
                ),
                _source(
                    "openrouter.routing",
                    "OpenRouter Provider Routing",
                    "https://openrouter.ai/docs/guides/routing/provider-selection",
                    "official_docs",
                ),
            ),
            relevance=("routing", "budget", "ZDR", "DLP", "BYOK"),
            observations=(
                "Do not describe OpenRouter as a routing-only dumb proxy.",
            ),
            capabilities=(
                "model_gateway",
                "provider_routing",
                "budget_control",
                "zdr",
                "prompt_injection_detection",
                "sensitive_data_filter",
                "byok",
            ),
            tags=frozenset({"market", "gateway", "adapter_candidate", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.langflow.2026",
            name="Langflow 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "Langflow supports visual agent flows, MCP, multi-agent composition and "
                "checkpointed human approval for gated tools."
            ),
            usage=(
                "Do not claim low-code agent builders lack HITL. Compare governance depth, "
                "evidence portability and operational assurance instead."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "langflow.tools",
                    "Langflow agent tools",
                    "https://docs.langflow.org/agents-tools",
                    "official_docs",
                ),
            ),
            relevance=("low-code", "HITL", "MCP", "multi-agent"),
            capabilities=("visual_workflow", "human_in_the_loop", "mcp", "multi_agent"),
            tags=frozenset({"market", "low_code", "competitor", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.flowise.2026",
            name="Flowise Agentflow V2 2026 capability snapshot",
            category="competitive_intelligence",
            summary=(
                "Flowise Agentflow V2 supports explicit orchestration, multi-agent work, "
                "checkpoint/resume and human approval for tool execution."
            ),
            usage=(
                "Treat Flowise as a serious low-code orchestration competitor, not a simple "
                "visual prompt builder."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "flowise.agentflow-v2",
                    "Flowise Agentflow V2",
                    "https://docs.flowiseai.com/using-flowise/agentflowv2",
                    "official_docs",
                ),
            ),
            relevance=("low-code", "multi-agent", "checkpoint", "HITL"),
            capabilities=(
                "visual_workflow",
                "multi_agent",
                "checkpointing",
                "human_in_the_loop",
                "tool_permissions",
            ),
            tags=frozenset({"market", "low_code", "competitor", "verified_2026"}),
        ),
        KnowledgeItem(
            item_id="market.typhoon.2026",
            name="Typhoon Thai AI 2026 capability snapshot",
            category="thai_ai",
            summary=(
                "Typhoon is a Thai-engineered model family covering agentic language models, "
                "function calling, OCR, ASR, vision, audio and translation."
            ),
            usage=(
                "Treat Typhoon as a strategic Thai model/provider candidate under CK-NEXUS "
                "governance rather than claiming no serious Thai AI competitors exist."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "typhoon.models",
                    "Typhoon models",
                    "https://docs.opentyphoon.ai/th/models/",
                    "official_docs",
                ),
            ),
            relevance=("Thai", "agentic model", "ASR", "OCR", "function calling"),
            observations=(
                "Thai language alone is not a defensible moat for CK-NEXUS.",
                "Differentiate through Thai assurance, governance and sovereign orchestration.",
            ),
            capabilities=(
                "thai_language",
                "agentic_model",
                "function_calling",
                "ocr",
                "asr",
                "multimodal",
            ),
            tags=frozenset({"market", "thai", "provider", "adapter_candidate"}),
        ),
        KnowledgeItem(
            item_id="market.assurance.wedge.2026",
            name="Evidence-native agent assurance market wedge",
            category="market_strategy",
            summary=(
                "A defensible CK-NEXUS wedge is portable evidence-by-construction across "
                "models, agents, tools and deployment environments rather than feature absence."
            ),
            usage=(
                "Build a provider-neutral assurance control plane that binds intent, policy, "
                "approval, execution, verification and evidence to exact execution identity."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "iso.42001",
                    "ISO/IEC 42001 AI management systems",
                    "https://www.iso.org/standard/42001",
                    "standard",
                ),
                _source(
                    "nist.ai.600-1",
                    "NIST AI RMF Generative AI Profile",
                    "https://www.nist.gov/publications/artificial-intelligence-risk-management-"
                    "framework-generative-artificial-intelligence",
                    "standard_guidance",
                ),
                _source(
                    "eu.ai-act",
                    "EU AI Act application timeline",
                    "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
                    "regulatory_source",
                ),
            ),
            relevance=("assurance", "compliance", "evidence", "regulated enterprise"),
            observations=(
                "This is a market inference, not proof that no competitor can build the feature.",
                "Position on enforced system invariants and portable proof, not absolute novelty.",
            ),
            capabilities=(
                "evidence_by_construction",
                "exact_subject_identity",
                "independent_verification",
                "policy_binding",
                "audit_replay",
                "compliance_mapping",
            ),
            tags=frozenset({"market", "strategy", "assurance", "regulated_enterprise"}),
        ),
    )
    return KnowledgeCatalog(items)
