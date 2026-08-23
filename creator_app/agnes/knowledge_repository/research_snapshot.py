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
            item_id="voice.piper",
            name="Piper text to speech",
            category="voice",
            summary="Local neural text-to-speech engine with a mature deployment history.",
            usage="Evaluate for offline and privacy-first voice fallback where voice licenses permit.",
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
            observations=("Upstream development moved; voice model licenses require separate review.",),
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
            usage="Align Design Intelligence token serialization with the published format model.",
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
    )
    return KnowledgeCatalog(items)
