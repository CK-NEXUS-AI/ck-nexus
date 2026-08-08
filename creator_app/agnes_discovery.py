from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class DiscoveryKind(StrEnum):
    SKILL_SPEC = "skill_spec"
    MCP_REGISTRY = "mcp_registry"
    AGENT_RUNTIME = "agent_runtime"
    WORKSPACE = "workspace"
    MODEL_CATALOG = "model_catalog"


@dataclass(frozen=True, slots=True)
class DiscoverySource:
    id: str
    kind: DiscoveryKind
    base_url: str
    trust: str
    auto_discover: bool
    auto_install: bool
    notes: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "base_url": self.base_url,
            "trust": self.trust,
            "auto_discover": self.auto_discover,
            "auto_install": self.auto_install,
            "notes": self.notes,
        }


TRUSTED_DISCOVERY_SOURCES: tuple[DiscoverySource, ...] = (
    DiscoverySource(
        "agent-skills-spec",
        DiscoveryKind.SKILL_SPEC,
        "https://agentskills.io",
        "open_standard",
        True,
        False,
        "Portable SKILL.md format; metadata may be discovered automatically, code remains review-gated.",
    ),
    DiscoverySource(
        "mcp-registry",
        DiscoveryKind.MCP_REGISTRY,
        "https://registry.modelcontextprotocol.io",
        "official_registry",
        True,
        False,
        "Discover MCP servers/tools; activation requires capability and security review.",
    ),
    DiscoverySource(
        "openai-agents-sdk",
        DiscoveryKind.AGENT_RUNTIME,
        "https://openai.github.io/openai-agents-python",
        "official_primary",
        True,
        False,
        "Reference runtime for tools, handoffs, guardrails, tracing and sandbox agents.",
    ),
    DiscoverySource(
        "agnes-open-source",
        DiscoveryKind.AGENT_RUNTIME,
        "https://agnescode.agnes-ai.com",
        "project_primary",
        True,
        False,
        "Optional external AGNES runtime/ACP/MCP integration; CK-NEXUS remains policy authority.",
    ),
    DiscoverySource(
        "e2b",
        DiscoveryKind.WORKSPACE,
        "https://e2b.dev",
        "provider_primary",
        True,
        False,
        "External isolated coding workspace candidate; requires brokered service authorization.",
    ),
    DiscoverySource(
        "github-codespaces",
        DiscoveryKind.WORKSPACE,
        "https://docs.github.com/en/rest/codespaces",
        "provider_primary",
        True,
        False,
        "Repository-bound development workspace; use GitHub App/fine-grained authorization.",
    ),
)


@dataclass(frozen=True, slots=True)
class CandidateReview:
    state: str
    reasons: tuple[str, ...]
    activation_allowed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reasons": list(self.reasons),
            "activation_allowed": self.activation_allowed,
        }


class SkillDiscoveryPolicy:
    """Metadata discovery may be automatic; executable skill activation is fail-closed."""

    def __init__(self, sources: tuple[DiscoverySource, ...] = TRUSTED_DISCOVERY_SOURCES) -> None:
        self.sources = sources
        self._allowed_hosts = {
            (urlparse(item.base_url).hostname or "").lower()
            for item in sources
        }

    def review_candidate(
        self,
        *,
        source_url: str,
        checksum_present: bool,
        license_known: bool,
        has_executable_scripts: bool,
        requests_credentials: bool,
        requests_network: bool,
    ) -> CandidateReview:
        host = (urlparse(source_url).hostname or "").lower()
        reasons: list[str] = []
        if host not in self._allowed_hosts:
            reasons.append("source host is not in the trusted discovery allowlist")
        if not checksum_present:
            reasons.append("source checksum/identity is missing")
        if not license_known:
            reasons.append("license is unknown")
        if has_executable_scripts:
            reasons.append("candidate contains executable scripts")
        if requests_credentials:
            reasons.append("candidate requests credential access")
        if requests_network:
            reasons.append("candidate requests network egress")
        if reasons:
            return CandidateReview("quarantined", tuple(reasons), False)
        return CandidateReview("metadata_verified", (), False)

    def source_catalog(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.sources]

    @staticmethod
    def model_watch_plan(limit: int = 50) -> dict[str, object]:
        bounded = max(1, min(int(limit), 50))
        return {
            "limit": bounded,
            "pipeline": [
                "collect newest model metadata from approved public catalogs",
                "deduplicate by provider/model/version alias",
                "resolve canonical provider identity",
                "verify release/capability claims against primary provider documentation",
                "classify modality, context, tool support, local/cloud, price/quota metadata",
                "run compatibility and policy checks",
                "queue benchmark/eval in isolated workspace",
                "append verified model record; mark older record superseded rather than deleting it",
            ],
            "auto_promote_to_runtime": False,
            "reason": "new models must pass verification and evals before routing traffic",
        }
