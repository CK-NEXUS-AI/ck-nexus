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


def _source(source_id: str, name: str, url: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        name=name,
        url=url,
        source_type="official_docs",
        discovered_at=_DISCOVERED_AT,
        evidence_level=EvidenceLevel.DOCUMENTED,
    )


def _item(
    *,
    item_id: str,
    name: str,
    category: str,
    summary: str,
    usage: str,
    source_id: str,
    source_name: str,
    source_url: str,
    mode: AdoptionMode,
    capabilities: tuple[str, ...],
    relevance: tuple[str, ...],
    observations: tuple[str, ...] = (),
) -> KnowledgeItem:
    return KnowledgeItem(
        item_id=item_id,
        name=name,
        category=category,
        summary=summary,
        usage=usage,
        status=KnowledgeStatus.ADOPTABLE,
        sources=(_source(source_id, source_name, source_url),),
        adoption_mode=mode,
        capabilities=capabilities,
        relevance=relevance,
        observations=observations,
        tags=frozenset({"universal_control_fabric", category, mode.value}),
    )


def universal_control_catalog() -> KnowledgeCatalog:
    """Documented systems that CK-NEXUS can adopt, wrap, or study.

    Inclusion never grants execution authority. Runtime activation still requires
    CK-NEXUS policy, verification, provenance, credentials, and environment evidence.
    """

    items = (
        _item(
            item_id="control.runtime.dapr_agents",
            name="Dapr Agents",
            category="durable_runtime",
            summary=(
                "Durable multi-agent runtime using Dapr workflows, state, messaging, "
                "resiliency, identity, MCP, and agents-as-tools."
            ),
            usage=(
                "Primary candidate for a portable durable runtime adapter under the "
                "CK-NEXUS Governor."
            ),
            source_id="dapr.agents.introduction",
            source_name="Dapr Agents introduction",
            source_url="https://docs.dapr.io/developing-applications/dapr-agents/dapr-agents-introduction/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "durable_execution",
                "multi_agent",
                "persistent_state",
                "resiliency",
                "mcp",
                "agents_as_tools",
                "pubsub",
            ),
            relevance=("AGNES runtime", "cross-framework control", "durable execution"),
            observations=(
                "Dapr now documents verifiable execution history; CK-NEXUS must not "
                "claim that signed or tamper-evident workflow history is unique.",
                "Dapr runtime evidence is input to CK verification, not production authority.",
            ),
        ),
        _item(
            item_id="control.runtime.temporal",
            name="Temporal",
            category="durable_runtime",
            summary=(
                "Open-source durable execution platform that resumes workflows after "
                "process, network, or infrastructure failures."
            ),
            usage="Wrap for long-lived, high-value workflows that need durable recovery.",
            source_id="temporal.what-is",
            source_name="Temporal documentation",
            source_url="https://docs.temporal.io/",
            mode=AdoptionMode.WRAP,
            capabilities=("durable_execution", "workflow_recovery", "long_running_tasks"),
            relevance=("mission runtime", "recovery", "human approval waits"),
        ),
        _item(
            item_id="control.runtime.restate",
            name="Restate",
            category="durable_runtime",
            summary=(
                "Durable runtime with built-in state, journals, exactly-once communication, "
                "timers, and agent/workflow recovery."
            ),
            usage="Wrap for journaled agent execution and stateful services.",
            source_id="restate.ai",
            source_name="Restate AI documentation",
            source_url="https://docs.restate.dev/ai",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "durable_execution",
                "execution_journal",
                "exactly_once",
                "stateful_services",
                "human_in_the_loop",
            ),
            relevance=("agent recovery", "execution journal", "long-running agents"),
        ),
        _item(
            item_id="control.runtime.dbos",
            name="DBOS",
            category="durable_runtime",
            summary=(
                "Postgres-backed durable workflow runtime with checkpoints and agent SDK "
                "integrations."
            ),
            usage="Wrap where Postgres-native durability reduces infrastructure complexity.",
            source_id="dbos.durable-workflows",
            source_name="DBOS durable workflows",
            source_url="https://docs.dbos.dev/python/tutorials/workflow-tutorial",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "durable_execution",
                "postgres_backed",
                "checkpointing",
                "agent_integration",
            ),
            relevance=("Postgres runtime", "durable agents", "reproducible workflows"),
        ),
        _item(
            item_id="control.runtime.inngest",
            name="Inngest",
            category="durable_runtime",
            summary=(
                "Event-driven durable execution with checkpointed agent steps, flow control, "
                "observability, and human interaction."
            ),
            usage="Wrap for event-driven agent jobs and production evaluation experiments.",
            source_id="inngest.durable-agents",
            source_name="Inngest Durable Agents",
            source_url="https://www.inngest.com/docs/guides/durable-agents",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "durable_execution",
                "event_driven",
                "checkpointing",
                "human_in_the_loop",
                "agent_evals",
            ),
            relevance=("event bus", "agent jobs", "evaluation"),
        ),
        _item(
            item_id="control.runtime.triggerdev",
            name="Trigger.dev",
            category="durable_runtime",
            summary=(
                "Durable TypeScript task platform with retries, queues, checkpoint-resume, "
                "streaming, observability, and human interaction."
            ),
            usage="Wrap for TypeScript-heavy long-running automation workloads.",
            source_id="trigger.dev.ai-agents",
            source_name="Trigger.dev AI agents",
            source_url="https://trigger.dev/ai-agents",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "durable_execution",
                "checkpoint_resume",
                "queues",
                "streaming",
                "human_in_the_loop",
            ),
            relevance=("TypeScript runtime", "background jobs", "long-running tasks"),
        ),
        _item(
            item_id="control.orchestration.kestra",
            name="Kestra",
            category="workflow_orchestration",
            summary=(
                "Open-source orchestration platform with code-defined workflows, AI agents, "
                "MCP resources, approvals, and rich control-flow primitives."
            ),
            usage="Wrap as an optional enterprise workflow engine behind CK policy.",
            source_id="kestra.ai-agents",
            source_name="Kestra AI agents",
            source_url="https://kestra.io/docs/how-to-guides/ai-agents",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "workflow_orchestration",
                "ai_agents",
                "mcp",
                "approval",
                "parallel_execution",
            ),
            relevance=("workflow engine", "approvals", "enterprise automation"),
        ),
        _item(
            item_id="control.orchestration.windmill",
            name="Windmill",
            category="workflow_orchestration",
            summary=(
                "Developer workflow platform with AI agent steps, scripts, flows, resources, "
                "and multiple model providers."
            ),
            usage="Study as a code-first automation adapter and developer tool surface.",
            source_id="windmill.ai-agent",
            source_name="Windmill AI Agent step",
            source_url="https://www.windmill.dev/docs/flows/ai_agent",
            mode=AdoptionMode.STUDY,
            capabilities=("workflow_orchestration", "ai_agent", "scripts", "resources"),
            relevance=("developer automation", "workflow builder", "multi-provider"),
        ),
        _item(
            item_id="control.policy.opa",
            name="Open Policy Agent",
            category="policy_authorization",
            summary=(
                "General-purpose policy-as-code engine with distributed enforcement, decision "
                "logs, bundles, and default-deny policy patterns."
            ),
            usage="Adopt as a policy decision adapter; CK-NEXUS remains policy authority.",
            source_id="opa.docs",
            source_name="Open Policy Agent documentation",
            source_url="https://www.openpolicyagent.org/docs/latest/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "policy_as_code",
                "default_deny",
                "distributed_enforcement",
                "decision_logs",
            ),
            relevance=("Policy Engine", "tool policy", "egress policy", "admission control"),
        ),
        _item(
            item_id="control.policy.cedar",
            name="Cedar Policy Language",
            category="policy_authorization",
            summary=(
                "Authorization policy language that separates principal/action/resource/context "
                "decisions from application business logic."
            ),
            usage="Study or wrap for deterministic authorization policy evaluation.",
            source_id="cedar.docs",
            source_name="Cedar documentation",
            source_url="https://docs.cedarpolicy.com/",
            mode=AdoptionMode.STUDY,
            capabilities=("authorization_policy", "principal_action_resource", "policy_as_code"),
            relevance=("authorization", "AgentCore comparison", "policy portability"),
        ),
        _item(
            item_id="control.authorization.openfga",
            name="OpenFGA",
            category="policy_authorization",
            summary=(
                "Relationship-based authorization with explicit guidance for agents, delegated "
                "tool permissions, and task-bounded grants."
            ),
            usage="Adopt for graph-based human/agent/resource authorization relationships.",
            source_id="openfga.agents",
            source_name="OpenFGA Authorization for Agents",
            source_url="https://openfga.dev/docs/modeling/ai-agents",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "relationship_authorization",
                "agent_identity",
                "delegated_access",
                "task_bounded_grants",
                "revocation",
            ),
            relevance=("agent permissions", "delegation", "resource authorization"),
        ),
        _item(
            item_id="control.authorization.cerbos",
            name="Cerbos",
            category="policy_authorization",
            summary=(
                "Authorization PDP and policy management platform for apps, APIs, services, "
                "AI agents, and MCP servers."
            ),
            usage="Study as an external PDP and policy distribution reference implementation.",
            source_id="cerbos.docs",
            source_name="Cerbos documentation",
            source_url="https://docs.cerbos.dev/",
            mode=AdoptionMode.STUDY,
            capabilities=("policy_decision_point", "default_deny", "mcp_policy", "audit"),
            relevance=("PDP", "policy distribution", "agent authorization"),
        ),
        _item(
            item_id="control.authorization.permit_mcp_gateway",
            name="Permit.io MCP Gateway",
            category="policy_authorization",
            summary=(
                "MCP proxy with authentication, fine-grained authorization, consent, audit, "
                "and deny-by-default tool-call enforcement."
            ),
            usage="Study and optionally wrap; reuse its MCP enforcement patterns where suitable.",
            source_id="permit.mcp-gateway",
            source_name="Permit.io MCP Gateway",
            source_url="https://docs.permit.io/integrations/mcp-gateway/overview",
            mode=AdoptionMode.STUDY,
            capabilities=(
                "mcp_gateway",
                "fine_grained_authorization",
                "consent",
                "tool_audit",
                "default_deny",
            ),
            relevance=("MCP Policy Gateway", "tool consent", "agent trust"),
        ),
        _item(
            item_id="control.identity.spiffe_spire",
            name="SPIFFE / SPIRE",
            category="identity",
            summary=(
                "Open standards and production software for workload identity, attestation, "
                "short-lived SVIDs, and workload APIs."
            ),
            usage="Adopt for machine/workload identity beneath CK execution identities.",
            source_id="spiffe.docs",
            source_name="SPIFFE documentation",
            source_url="https://spiffe.io/docs/latest/spiffe-about/overview/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "workload_identity",
                "attestation",
                "short_lived_credentials",
                "svid",
                "zero_trust",
            ),
            relevance=("execution identity", "service identity", "zero trust"),
        ),
        _item(
            item_id="control.protocol.mcp",
            name="Model Context Protocol",
            category="interoperability_protocol",
            summary=(
                "Standard protocol for connecting AI applications to tools, data, resources, "
                "and external capabilities."
            ),
            usage="Adopt as the tool/data interoperability spine behind CK trust enforcement.",
            source_id="mcp.spec",
            source_name="Model Context Protocol specification",
            source_url="https://modelcontextprotocol.io/specification/2025-06-18",
            mode=AdoptionMode.ADOPT,
            capabilities=("tool_protocol", "resource_protocol", "client_server", "authorization"),
            relevance=("Tool Fabric", "Connector Fabric", "MCP Policy Gateway"),
            observations=(
                "Track newer MCP specifications separately; protocol support never bypasses "
                "CK-NEXUS tool trust or consent policy.",
            ),
        ),
        _item(
            item_id="control.protocol.a2a",
            name="Agent2Agent Protocol",
            category="interoperability_protocol",
            summary=(
                "Open agent-to-agent interoperability protocol with discovery, task lifecycle, "
                "async collaboration, and protocol bindings."
            ),
            usage="Adopt as the external agent interoperability boundary.",
            source_id="a2a.spec",
            source_name="A2A Protocol specification",
            source_url="https://a2a-protocol.org/latest/specification/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "agent_interoperability",
                "agent_discovery",
                "task_lifecycle",
                "async_collaboration",
            ),
            relevance=("Agent Fabric", "cross-vendor agents", "external agent delegation"),
        ),
        _item(
            item_id="control.protocol.agui",
            name="AG-UI",
            category="interoperability_protocol",
            summary=(
                "Event-based bi-directional protocol between agent backends and user-facing "
                "applications with shared state and human interaction."
            ),
            usage="Adopt as a UI/event adapter while CK events remain canonical authority.",
            source_id="agui.docs",
            source_name="AG-UI documentation",
            source_url="https://docs.ag-ui.com/introduction",
            mode=AdoptionMode.ADOPT,
            capabilities=("agent_ui_protocol", "event_stream", "shared_state", "human_in_loop"),
            relevance=("Cognitive Control Universe", "event-driven UI", "Generative UI"),
        ),
        _item(
            item_id="control.connector.pipedream",
            name="Pipedream Connect",
            category="connector_fabric",
            summary=(
                "Managed-auth integration platform exposing thousands of apps and tools with "
                "API proxy, workflows, and MCP access."
            ),
            usage="Wrap for long-tail connectors; keep OAuth and scopes behind CK governance.",
            source_id="pipedream.connect",
            source_name="Pipedream Connect",
            source_url="https://pipedream.com/docs/connect",
            mode=AdoptionMode.WRAP,
            capabilities=("managed_auth", "connector_catalog", "tool_catalog", "mcp", "api_proxy"),
            relevance=("Connector Fabric", "JIT tool discovery", "long-tail SaaS"),
        ),
        _item(
            item_id="control.connector.composio",
            name="Composio",
            category="connector_fabric",
            summary=(
                "Agent tool and authentication platform with tool discovery, hosted MCP, and "
                "actions across a large integration catalog."
            ),
            usage="Wrap as an agent-tool provider behind Connector Registry and policy gates.",
            source_id="composio.docs",
            source_name="Composio documentation",
            source_url="https://docs.composio.dev/",
            mode=AdoptionMode.WRAP,
            capabilities=("managed_auth", "tool_discovery", "hosted_mcp", "connector_catalog"),
            relevance=("Connector Fabric", "JIT tools", "agent integrations"),
        ),
        _item(
            item_id="control.connector.nango",
            name="Nango",
            category="connector_fabric",
            summary=(
                "Open-source integration infrastructure for OAuth/API auth, token refresh, "
                "syncs, actions, webhooks, retries, and resumable functions."
            ),
            usage="Wrap for code-first OAuth and durable integration sync/action adapters.",
            source_id="nango.docs",
            source_name="Nango documentation",
            source_url="https://docs.nango.dev/",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "managed_auth",
                "token_refresh",
                "sync",
                "actions",
                "webhooks",
                "resumable_functions",
            ),
            relevance=("Credential Broker", "Connector Fabric", "data synchronization"),
        ),
        _item(
            item_id="control.connector.activepieces",
            name="Activepieces",
            category="connector_fabric",
            summary=(
                "Open-source automation platform with self-hosting, AI agents, HITL, pieces, "
                "project scoping, and built-in MCP server support."
            ),
            usage="Adopt as an optional self-hosted connector/workflow surface alongside n8n.",
            source_id="activepieces.docs",
            source_name="Activepieces documentation",
            source_url="https://www.activepieces.com/docs",
            mode=AdoptionMode.ADOPT,
            capabilities=("self_hosted", "workflow_automation", "mcp", "ai_agents", "hitl"),
            relevance=("n8n complement", "air-gapped automation", "connector catalog"),
        ),
        _item(
            item_id="control.observability.langfuse",
            name="Langfuse",
            category="observability_evaluation",
            summary=(
                "Open-source LLM observability and evaluation platform with tracing, costs, "
                "datasets, experiments, and OpenTelemetry ingestion."
            ),
            usage="Wrap as an observability/evaluation sink; CK Evidence remains authoritative.",
            source_id="langfuse.docs",
            source_name="Langfuse documentation",
            source_url="https://langfuse.com/docs",
            mode=AdoptionMode.WRAP,
            capabilities=("llm_tracing", "opentelemetry", "evaluation", "datasets", "costs"),
            relevance=("Observability Plane", "agent evaluation", "model monitoring"),
        ),
        _item(
            item_id="control.observability.phoenix",
            name="Arize Phoenix",
            category="observability_evaluation",
            summary=(
                "Open-source AI observability and evaluation platform using OpenTelemetry and "
                "OpenInference with traces, datasets, experiments, and evaluators."
            ),
            usage="Wrap as a second observer/evaluator for independent development comparison.",
            source_id="phoenix.docs",
            source_name="Arize Phoenix documentation",
            source_url="https://arize.com/docs/phoenix",
            mode=AdoptionMode.WRAP,
            capabilities=("opentelemetry", "openinference", "tracing", "evaluation", "datasets"),
            relevance=("independent evaluation", "tool-call evaluation", "observability"),
        ),
        _item(
            item_id="control.memory.graphiti",
            name="Graphiti",
            category="memory_context",
            summary=(
                "Open-source temporal context graph with incremental updates, hybrid search, "
                "changing facts, point-in-time retrieval, and source episodes."
            ),
            usage=(
                "Adopt as a temporal knowledge projection and retrieval index, never as the "
                "canonical CK history authority."
            ),
            source_id="graphiti.github",
            source_name="Graphiti repository",
            source_url="https://github.com/getzep/graphiti",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "temporal_knowledge_graph",
                "hybrid_search",
                "incremental_updates",
                "point_in_time_query",
                "provenance",
            ),
            relevance=("Knowledge Repository", "Reuse Engine", "evolution graph"),
            observations=(
                "Graph projections must be rebuildable from CK-NEXUS canonical history.",
            ),
        ),
        _item(
            item_id="control.memory.zep",
            name="Zep",
            category="memory_context",
            summary=(
                "Managed agent memory and context platform using temporal knowledge graphs and "
                "governed context infrastructure."
            ),
            usage="Wrap only as an optional managed context provider; preserve CK authority.",
            source_id="zep.docs",
            source_name="Zep documentation",
            source_url="https://help.getzep.com/",
            mode=AdoptionMode.WRAP,
            capabilities=("agent_memory", "temporal_graph", "context_retrieval", "governance"),
            relevance=("managed memory", "context engineering", "knowledge graph"),
        ),
        _item(
            item_id="control.sandbox.daytona",
            name="Daytona",
            category="sandbox_execution",
            summary=(
                "Elastic secure sandboxes for agent-generated code with isolated kernels, "
                "filesystems, networking, resources, and snapshots."
            ),
            usage="Wrap as a remote disposable sandbox provider under CK execution policy.",
            source_id="daytona.docs",
            source_name="Daytona documentation",
            source_url="https://www.daytona.io/docs/",
            mode=AdoptionMode.WRAP,
            capabilities=("sandbox", "code_execution", "isolation", "snapshots", "gpu"),
            relevance=("Execution Kernel", "untrusted code", "remote sandbox"),
        ),
        _item(
            item_id="control.sandbox.e2b",
            name="E2B",
            category="sandbox_execution",
            summary=(
                "Cloud agent sandboxes using Firecracker microVM isolation with filesystem, "
                "commands, code execution, networking, and BYOC options."
            ),
            usage="Wrap as an optional cloud sandbox; require exact environment evidence.",
            source_id="e2b.docs",
            source_name="E2B documentation",
            source_url="https://e2b.dev/docs",
            mode=AdoptionMode.WRAP,
            capabilities=("microvm_sandbox", "code_execution", "filesystem", "networking"),
            relevance=("Execution Kernel", "untrusted code", "cloud sandbox"),
        ),
        _item(
            item_id="control.browser.browserbase",
            name="Browserbase / Stagehand",
            category="browser_execution",
            summary=(
                "Managed browser infrastructure and AI browser automation with Playwright, "
                "persistent sessions, recordings, and model-provider-neutral control."
            ),
            usage="Wrap only through External Access Governance and browser policy enforcement.",
            source_id="browserbase.stagehand",
            source_name="Stagehand documentation",
            source_url="https://docs.stagehand.dev/",
            mode=AdoptionMode.WRAP,
            capabilities=("browser_automation", "playwright", "session_recording", "webmcp"),
            relevance=("Browser Intelligence", "web automation", "auditable browser sessions"),
            observations=(
                "CK-NEXUS must not use browser automation to bypass CAPTCHA, ACLs, login "
                "controls, or other authorization boundaries.",
            ),
        ),
        _item(
            item_id="control.inference.ollama",
            name="Ollama",
            category="local_inference",
            summary=(
                "Local model runtime with OpenAI-compatible APIs, tool calling, streaming, and "
                "structured outputs."
            ),
            usage="Adopt as a local inference adapter after model-locality verification.",
            source_id="ollama.docs",
            source_name="Ollama documentation",
            source_url="https://docs.ollama.com/",
            mode=AdoptionMode.ADOPT,
            capabilities=("local_inference", "tool_calling", "structured_outputs", "openai_api"),
            relevance=("Zero-Cost Runtime", "offline inference", "local-first routing"),
            observations=(
                "The zero-cost lane must continue rejecting remote/cloud model metadata.",
            ),
        ),
        _item(
            item_id="control.inference.vllm",
            name="vLLM",
            category="local_inference",
            summary=(
                "High-throughput self-hosted model serving with OpenAI-compatible APIs and "
                "tool/function calling support."
            ),
            usage="Adopt for high-throughput sovereign inference behind CK network controls.",
            source_id="vllm.openai-server",
            source_name="vLLM OpenAI-compatible server",
            source_url=(
                "https://docs.vllm.ai/en/latest/serving/"
                "openai_compatible_server/"
            ),
            mode=AdoptionMode.ADOPT,
            capabilities=("self_hosted_inference", "openai_api", "tool_calling", "high_throughput"),
            relevance=("Model Fabric", "GPU inference", "sovereign deployment"),
            observations=(
                "Place vLLM behind CK authentication/reverse-proxy controls; do not expose "
                "management surfaces based on an API key assumption alone.",
            ),
        ),
    )
    return KnowledgeCatalog(items)
