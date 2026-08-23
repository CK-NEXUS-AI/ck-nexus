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
        tags=frozenset({"infrastructure_control_fabric", category, mode.value}),
    )


def infrastructure_control_catalog() -> KnowledgeCatalog:
    """Infrastructure and platform systems reusable beneath CK-NEXUS authority."""

    items = (
        _item(
            item_id="infra.control.kubernetes",
            name="Kubernetes",
            category="infrastructure_control",
            summary=(
                "Declarative control plane whose controllers continuously reconcile workload "
                "objects toward desired state."
            ),
            usage="Adopt as a deployment substrate, not as CK-NEXUS policy authority.",
            source_id="kubernetes.workload-management",
            source_name="Kubernetes Workload Management",
            source_url="https://kubernetes.io/docs/concepts/workloads/controllers/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "desired_state",
                "workload_reconciliation",
                "self_healing",
                "declarative_api",
            ),
            relevance=("runtime hosting", "worker fleet", "self-healing deployment"),
        ),
        _item(
            item_id="infra.control.crossplane",
            name="Crossplane",
            category="infrastructure_control",
            summary=(
                "Control-plane framework that exposes custom APIs to manage applications, "
                "cloud resources, and external software with continuous reconciliation."
            ),
            usage=(
                "Adopt as an infrastructure/provider control adapter so CK-NEXUS can govern "
                "many external systems through desired-state APIs."
            ),
            source_id="crossplane.what-is",
            source_name="What is Crossplane?",
            source_url="https://docs.crossplane.io/latest/whats-crossplane/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "universal_control_plane",
                "custom_api",
                "cloud_resource_management",
                "drift_reconciliation",
                "composition",
            ),
            relevance=("multi-cloud control", "GitHub resources", "platform engineering"),
            observations=(
                "Crossplane can control external resources, but CK-NEXUS approval and evidence "
                "must remain outside provider reconciliation authority.",
            ),
        ),
        _item(
            item_id="infra.workflow.argo",
            name="Argo Workflows",
            category="infrastructure_workflow",
            summary=(
                "Container-native Kubernetes workflow engine supporting DAGs, parallel jobs, "
                "templates, archives, cron workflows, APIs, and artifact handling."
            ),
            usage="Wrap for Kubernetes-native batch, ML, CI, and infrastructure workflows.",
            source_id="argo.workflows",
            source_name="Argo Workflows documentation",
            source_url="https://argo-workflows.readthedocs.io/en/latest/",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "dag_workflow",
                "parallel_jobs",
                "workflow_archive",
                "cron",
                "kubernetes_native",
            ),
            relevance=("batch jobs", "ML pipelines", "infrastructure automation"),
        ),
        _item(
            item_id="infra.event.nats",
            name="NATS / JetStream",
            category="event_backbone",
            summary=(
                "High-performance messaging system with JetStream persistence for durable "
                "event and message workflows."
            ),
            usage="Adopt as a lightweight event backbone candidate for CK runtime events.",
            source_id="nats.docs",
            source_name="NATS documentation",
            source_url="https://docs.nats.io/",
            mode=AdoptionMode.ADOPT,
            capabilities=("messaging", "pubsub", "event_stream", "persistence", "jetstream"),
            relevance=("Runtime Event Bus", "agent messaging", "distributed workers"),
            observations=(
                "Message durability does not itself prove CK-NEXUS semantic verification.",
            ),
        ),
        _item(
            item_id="infra.event.knative",
            name="Knative Eventing",
            category="event_backbone",
            summary=(
                "Event-driven APIs using sources, brokers, triggers, sinks, and CloudEvents for "
                "loosely coupled routing on Kubernetes."
            ),
            usage="Wrap when Kubernetes event routing and CloudEvents interoperability help.",
            source_id="knative.eventing",
            source_name="Knative Eventing overview",
            source_url="https://knative.dev/docs/eventing/",
            mode=AdoptionMode.WRAP,
            capabilities=("cloudevents", "broker", "trigger", "event_routing", "kubernetes"),
            relevance=("event fabric", "integration events", "serverless workflows"),
        ),
        _item(
            item_id="infra.observability.opentelemetry",
            name="OpenTelemetry",
            category="observability_protocol",
            summary=(
                "Vendor-neutral observability framework for generating, collecting, and "
                "exporting traces, metrics, and logs across runtimes and backends."
            ),
            usage="Adopt as the canonical telemetry transport and semantic instrumentation layer.",
            source_id="otel.docs",
            source_name="OpenTelemetry documentation",
            source_url="https://opentelemetry.io/docs/",
            mode=AdoptionMode.ADOPT,
            capabilities=("traces", "metrics", "logs", "collector", "vendor_neutral"),
            relevance=("Observability Plane", "Langfuse", "Phoenix", "cross-runtime telemetry"),
            observations=(
                "Telemetry is operational evidence input, not automatic verification authority.",
            ),
        ),
        _item(
            item_id="infra.secrets.openbao",
            name="OpenBao",
            category="credential_backend",
            summary=(
                "Identity-based secrets and encryption system with dynamic credentials, leases, "
                "revocation, PKI, audit devices, and policy-controlled access."
            ),
            usage="Adopt as an open secret backend option behind CK Credential Broker contracts.",
            source_id="openbao.what-is",
            source_name="What is OpenBao?",
            source_url="https://openbao.org/docs/what-is-openbao/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "dynamic_secrets",
                "secret_leases",
                "revocation",
                "pki",
                "encryption",
                "audit",
            ),
            relevance=("Credential Broker", "short-lived credentials", "secret rotation"),
            observations=(
                "CK-NEXUS should store opaque credential references, not secret material in "
                "memory, prompts, evidence, or repository files.",
            ),
        ),
        _item(
            item_id="infra.secrets.vault",
            name="HashiCorp Vault",
            category="credential_backend",
            summary=(
                "Secrets platform supporting dynamic secret leases, renewal, revocation, and "
                "credential lifecycle management."
            ),
            usage="Wrap as an alternative enterprise secret backend behind Credential Broker.",
            source_id="vault.leases",
            source_name="Vault lease, renew, and revoke",
            source_url="https://developer.hashicorp.com/vault/docs/concepts/lease",
            mode=AdoptionMode.WRAP,
            capabilities=("dynamic_secrets", "secret_leases", "renewal", "revocation"),
            relevance=("enterprise secrets", "Credential Broker", "credential lifecycle"),
        ),
        _item(
            item_id="infra.compute.ray",
            name="Ray / Ray Serve",
            category="distributed_compute",
            summary=(
                "Distributed Python runtime for tasks and stateful actors, plus scalable model "
                "and LLM serving across GPUs and nodes."
            ),
            usage="Wrap for distributed agent workers, evaluation jobs, and large model serving.",
            source_id="ray.core-concepts",
            source_name="Ray Core key concepts",
            source_url="https://docs.ray.io/en/latest/ray-core/key-concepts.html",
            mode=AdoptionMode.WRAP,
            capabilities=(
                "distributed_tasks",
                "stateful_actors",
                "resource_scheduling",
                "multi_node",
                "gpu_compute",
            ),
            relevance=("Agent Fabric", "evaluation swarm", "distributed inference"),
        ),
        _item(
            item_id="infra.inference.bentoml",
            name="BentoML / BentoCloud Gateway",
            category="inference_platform",
            summary=(
                "Model/application serving stack with local OCI packaging and gateway support "
                "for routing across clouds, regions, vendors, and heterogeneous GPU fleets."
            ),
            usage="Study or wrap for multi-region inference fleet abstraction.",
            source_id="bentoml.gateways",
            source_name="BentoCloud Gateways",
            source_url=(
                "https://docs.bentoml.com/en/latest/scale-with-bentocloud/"
                "scaling/gateways.html"
            ),
            mode=AdoptionMode.STUDY,
            capabilities=(
                "model_serving",
                "multi_region",
                "multi_cloud",
                "gpu_gateway",
                "load_balancing",
            ),
            relevance=("Model Fabric", "GPU fleet", "multi-cloud inference"),
        ),
        _item(
            item_id="infra.scaling.keda",
            name="KEDA",
            category="resource_governance",
            summary=(
                "Kubernetes event-driven autoscaler that scales deployments, stateful sets, "
                "jobs, and custom resources from many event sources."
            ),
            usage="Adopt for bounded event-driven worker scaling under CK resource policy.",
            source_id="keda.docs",
            source_name="KEDA documentation",
            source_url="https://keda.sh/docs/2.20/",
            mode=AdoptionMode.ADOPT,
            capabilities=("event_autoscaling", "scale_to_zero", "jobs", "scalers", "kubernetes"),
            relevance=("Resource Governor", "worker autoscaling", "cost control"),
        ),
        _item(
            item_id="infra.flags.openfeature",
            name="OpenFeature",
            category="runtime_configuration",
            summary=(
                "Vendor-agnostic feature-flag specification and SDK abstraction that can switch "
                "or combine flag providers without code-level lock-in."
            ),
            usage="Adopt for governed rollout, canary, kill-switch, and capability activation.",
            source_id="openfeature.intro",
            source_name="OpenFeature introduction",
            source_url="https://openfeature.dev/docs/reference/intro/",
            mode=AdoptionMode.ADOPT,
            capabilities=(
                "feature_flags",
                "vendor_neutral",
                "runtime_configuration",
                "canary",
                "kill_switch",
            ),
            relevance=("Feature Gate", "safe rollout", "circuit breaker", "experimentation"),
        ),
    )
    return KnowledgeCatalog(items)
