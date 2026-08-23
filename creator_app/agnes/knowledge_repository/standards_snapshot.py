from __future__ import annotations

from datetime import UTC, datetime

from .catalog import KnowledgeCatalog
from .models import (
    AdoptionMode,
    EvidenceLevel,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeStatus,
)

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


def standards_catalog() -> KnowledgeCatalog:
    """Current standards and reference implementations relevant to AGNES.

    Entries are documented references only. Catalog presence never means installed,
    configured, authorized, executed, verified, or production-approved.
    """

    items = (
        KnowledgeItem(
            item_id="standard.mcp.2026_07_28",
            name="Model Context Protocol 2026-07-28",
            category="interoperability_standard",
            summary=(
                "Current MCP revision with a stateless core, self-describing requests, "
                "header routing, cacheable list results, MRTR, extensions, and hardened auth."
            ),
            usage=(
                "Use as the protocol baseline for CK-NEXUS MCP adapters and reconcile older "
                "catalog references against this exact revision."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "mcp.2026-07-28",
                    "MCP 2026-07-28 specification release",
                    "https://blog.modelcontextprotocol.io/posts/2026-07-28/",
                    "official_release",
                ),
            ),
            adoption_mode=AdoptionMode.ADOPT,
            relevance=("Connector Fabric", "Tool Fabric", "MCP Policy Gateway"),
            observations=(
                "The repository runtime already pins MCP_PROTOCOL_VERSION 2026-07-28.",
                "Older 2025-06-18 catalog references are stale for the current runtime baseline.",
                "MCP interoperability never bypasses CK-NEXUS authorization or evidence policy.",
            ),
            capabilities=(
                "stateless_protocol",
                "tool_protocol",
                "resource_protocol",
                "header_routing",
                "cacheable_discovery",
                "multi_round_trip_requests",
                "authorization_hardening",
                "extensions",
            ),
            tags=frozenset({"standard", "mcp", "current_baseline"}),
        ),
        KnowledgeItem(
            item_id="standard.a2a.v1_0",
            name="Agent2Agent Protocol v1.0",
            category="interoperability_standard",
            summary=(
                "First stable production-ready A2A release for cross-vendor agent communication "
                "with version negotiation and enterprise trust features."
            ),
            usage=(
                "Use as the external agent-to-agent interoperability baseline while MCP remains "
                "the complementary tool and context protocol."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "a2a.v1.0",
                    "A2A Protocol v1.0 announcement",
                    "https://a2a-protocol.org/latest/announcing-1.0/",
                    "official_release",
                ),
            ),
            adoption_mode=AdoptionMode.ADOPT,
            relevance=("Agent Fabric", "cross-vendor agents", "external delegation"),
            observations=(
                "Pin integrations to a tested A2A version instead of an unqualified latest URL.",
                "Agent Cards and protocol identity are discovery inputs, not CK authority.",
            ),
            capabilities=(
                "agent_interoperability",
                "version_negotiation",
                "multi_protocol_bindings",
                "signed_agent_cards",
                "multi_tenancy",
                "agent_discovery",
            ),
            tags=frozenset({"standard", "a2a", "v1_0"}),
        ),
        KnowledgeItem(
            item_id="standard.opentelemetry.semconv.1_44",
            name="OpenTelemetry Semantic Conventions 1.44",
            category="observability_standard",
            summary=(
                "Vendor-neutral telemetry semantic conventions for traces, metrics, logs and "
                "resources; Generative AI conventions now live in the dedicated GenAI repository."
            ),
            usage=(
                "Use OpenTelemetry as the canonical telemetry transport vocabulary and track "
                "GenAI semantic conventions separately from older moved attributes."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "otel.semconv.1.44",
                    "OpenTelemetry semantic conventions 1.44.0",
                    "https://opentelemetry.io/docs/specs/semconv/",
                    "official_standard",
                ),
            ),
            adoption_mode=AdoptionMode.ADOPT,
            relevance=("Observability Plane", "agent tracing", "model telemetry"),
            observations=(
                "Telemetry is evidence input and does not automatically verify a claim.",
                "Do not rely on deprecated GenAI registry attributes after they move to the GenAI conventions repository.",
                "Sensitive prompts, retrieved content, and tool data require separate privacy policy before capture.",
            ),
            capabilities=(
                "traces",
                "metrics",
                "logs",
                "semantic_conventions",
                "genai_telemetry",
                "vendor_neutral",
            ),
            tags=frozenset({"standard", "opentelemetry", "observability"}),
        ),
        KnowledgeItem(
            item_id="standard.nist.ai_rmf_genai",
            name="NIST AI RMF Generative AI Profile",
            category="risk_management_standard",
            summary=(
                "NIST AI 600-1 profile for applying the AI Risk Management Framework to "
                "generative AI risks and controls."
            ),
            usage="Use as a governance and risk mapping reference, not as a certification claim.",
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "nist.ai.600-1",
                    "NIST AI RMF Generative AI Profile",
                    "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
                    "standard_guidance",
                ),
            ),
            adoption_mode=AdoptionMode.STUDY,
            relevance=("Security Governance", "AI risk", "assurance"),
            observations=(
                "Framework alignment must be backed by control mappings and evidence.",
                "Do not describe framework use as NIST certification.",
            ),
            capabilities=("ai_risk_management", "genai_risk_profile", "control_mapping"),
            tags=frozenset({"standard", "nist", "risk_management"}),
        ),
        KnowledgeItem(
            item_id="standard.iso.iec.42001",
            name="ISO/IEC 42001",
            category="management_standard",
            summary="AI management system standard for organizational AI governance.",
            usage=(
                "Use for management-system structure and evidence mapping; certification requires "
                "a separate accredited assessment process."
            ),
            status=KnowledgeStatus.UNDERSTOOD,
            sources=(
                _source(
                    "iso.42001",
                    "ISO/IEC 42001 AI management systems",
                    "https://www.iso.org/standard/42001",
                    "standard",
                ),
            ),
            adoption_mode=AdoptionMode.STUDY,
            relevance=("Enterprise Controls", "AI governance", "audit readiness"),
            observations=(
                "Internal conformance mapping is not equivalent to external certification.",
            ),
            capabilities=("ai_management_system", "governance", "audit_mapping"),
            tags=frozenset({"standard", "iso", "governance"}),
        ),
        KnowledgeItem(
            item_id="standard.wcag.2_2",
            name="WCAG 2.2",
            category="accessibility_standard",
            summary="W3C accessibility recommendation with testable success criteria.",
            usage="Use as the minimum accessibility baseline for CK-NEXUS and AGNES interfaces.",
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "w3c.wcag22",
                    "Web Content Accessibility Guidelines 2.2",
                    "https://www.w3.org/TR/WCAG22/",
                    "standard",
                ),
            ),
            adoption_mode=AdoptionMode.ADOPT,
            relevance=("Design Intelligence", "UI verification", "accessibility"),
            observations=(
                "Accessibility claims require test evidence against applicable success criteria.",
            ),
            capabilities=("accessibility", "testable_criteria", "inclusive_design"),
            tags=frozenset({"standard", "wcag", "accessibility"}),
        ),
        KnowledgeItem(
            item_id="reference.openai.agents_sdk",
            name="OpenAI Agents SDK",
            category="agent_runtime_reference",
            summary=(
                "Agent SDK with agents, handoffs, guardrails, sessions, human approval, tracing, "
                "and MCP integration."
            ),
            usage=(
                "Wrap as an intelligence and agent-runtime provider where useful; keep CK-NEXUS "
                "as authority for policy, approval, execution eligibility, and evidence promotion."
            ),
            status=KnowledgeStatus.ADOPTABLE,
            sources=(
                _source(
                    "openai.agents-sdk",
                    "OpenAI Agents SDK documentation",
                    "https://openai.github.io/openai-agents-python/",
                    "official_docs",
                ),
            ),
            adoption_mode=AdoptionMode.WRAP,
            relevance=("Agent Fabric", "guardrails", "HITL", "tracing", "MCP"),
            observations=(
                "Do not duplicate SDK primitives that can be safely adapted.",
                "Provider guardrails and traces do not self-approve CK production actions.",
            ),
            capabilities=(
                "agents",
                "handoffs",
                "guardrails",
                "persistent_sessions",
                "human_in_the_loop",
                "tracing",
                "mcp",
            ),
            tags=frozenset({"reference", "agent_sdk", "wrap"}),
        ),
    )
    return KnowledgeCatalog(items)
