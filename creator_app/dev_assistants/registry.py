"""Curated development-assistant registry for CK-NEXUS.

Only upstream projects with a clear official source are listed as active.
Open-source software is not the same thing as free model inference, so each
entry records the free-entry path separately from model/provider cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssistantStatus(StrEnum):
    """Lifecycle state used by the development-assistant fabric."""

    ACTIVE = "active"
    REFERENCE_ONLY = "reference_only"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class AssistantSpec:
    """Metadata required to safely discover and route a developer assistant."""

    assistant_id: str
    name: str
    upstream: str
    license: str
    status: AssistantStatus
    commands: tuple[str, ...]
    capabilities: frozenset[str]
    free_entry_path: str
    inference_may_cost: bool
    notes: str


ASSISTANTS: tuple[AssistantSpec, ...] = (
    AssistantSpec(
        assistant_id="opencode",
        name="OpenCode",
        upstream="https://github.com/anomalyco/opencode",
        license="MIT",
        status=AssistantStatus.ACTIVE,
        commands=("opencode",),
        capabilities=frozenset({"code_edit", "repo_analysis", "shell", "subagents"}),
        free_entry_path="Open-source CLI; can use local or separately configured models.",
        inference_may_cost=True,
        notes="Already has a CK-NEXUS control bridge; keep provider credentials brokered.",
    ),
    AssistantSpec(
        assistant_id="gemini_cli",
        name="Gemini CLI",
        upstream="https://github.com/google-gemini/gemini-cli",
        license="Apache-2.0",
        status=AssistantStatus.ACTIVE,
        commands=("gemini",),
        capabilities=frozenset({"code_edit", "repo_analysis", "shell", "web", "mcp"}),
        free_entry_path="Personal Google-account free tier is available upstream.",
        inference_may_cost=False,
        notes="Use OAuth/login flow; never copy account tokens into CK-NEXUS source.",
    ),
    AssistantSpec(
        assistant_id="cline",
        name="Cline",
        upstream="https://github.com/cline/cline",
        license="Apache-2.0",
        status=AssistantStatus.ACTIVE,
        commands=("cline",),
        capabilities=frozenset({"code_edit", "repo_analysis", "shell", "mcp", "parallel"}),
        free_entry_path="Open-source CLI/SDK; model/provider charges may still apply.",
        inference_may_cost=True,
        notes="Prefer headless/SDK usage inside isolated worktrees with CK-NEXUS review gates.",
    ),
    AssistantSpec(
        assistant_id="aider",
        name="Aider",
        upstream="https://github.com/Aider-AI/aider",
        license="Apache-2.0",
        status=AssistantStatus.ACTIVE,
        commands=("aider",),
        capabilities=frozenset({"code_edit", "repo_analysis", "git", "test_fix"}),
        free_entry_path="Open-source CLI; supports local models such as Ollama.",
        inference_may_cost=True,
        notes="Strong fit for scoped edit/test loops; commits remain development evidence only.",
    ),
    AssistantSpec(
        assistant_id="openhands",
        name="OpenHands",
        upstream="https://github.com/All-Hands-AI/OpenHands",
        license="MIT core",
        status=AssistantStatus.ACTIVE,
        commands=("openhands",),
        capabilities=frozenset({"code_edit", "repo_analysis", "agent_sdk", "sandbox"}),
        free_entry_path="Core agent stack is open source; bring your own model/runtime.",
        inference_may_cost=True,
        notes="Run only in isolated development environments; enterprise directory has separate terms.",
    ),
    AssistantSpec(
        assistant_id="goose",
        name="goose",
        upstream="https://github.com/aaif-goose/goose",
        license="Apache-2.0",
        status=AssistantStatus.ACTIVE,
        commands=("goose",),
        capabilities=frozenset({"code_edit", "workflow", "mcp", "local_agent"}),
        free_entry_path="Open-source local agent; model/provider charges may still apply.",
        inference_may_cost=True,
        notes="Use MCP extensions through CK-NEXUS capability boundaries, not direct secret sharing.",
    ),
    AssistantSpec(
        assistant_id="mini_swe_agent",
        name="mini-swe-agent",
        upstream="https://github.com/SWE-agent/mini-swe-agent",
        license="MIT",
        status=AssistantStatus.ACTIVE,
        commands=("mini", "mini-swe-agent"),
        capabilities=frozenset({"issue_fix", "repo_analysis", "sandbox", "benchmark"}),
        free_entry_path="Open-source software-engineering agent; model runtime is separate.",
        inference_may_cost=True,
        notes="Prefer it over legacy SWE-agent for small isolated issue-fix experiments.",
    ),
    AssistantSpec(
        assistant_id="ollama",
        name="Ollama",
        upstream="https://github.com/ollama/ollama",
        license="MIT",
        status=AssistantStatus.ACTIVE,
        commands=("ollama",),
        capabilities=frozenset({"local_model", "offline", "provider_backend"}),
        free_entry_path="Runs open/local models on user-controlled hardware.",
        inference_may_cost=False,
        notes="Treat as a model backend, not as CK-NEXUS decision authority.",
    ),
    AssistantSpec(
        assistant_id="mcp_reference_servers",
        name="MCP Reference Servers",
        upstream="https://github.com/modelcontextprotocol/servers",
        license="mixed/reference",
        status=AssistantStatus.REFERENCE_ONLY,
        commands=(),
        capabilities=frozenset({"mcp", "reference"}),
        free_entry_path="Reference implementations are publicly available.",
        inference_may_cost=False,
        notes="Reference code is not production-ready by default; threat-model before adoption.",
    ),
    AssistantSpec(
        assistant_id="continue",
        name="Continue",
        upstream="https://github.com/continuedev/continue",
        license="Apache-2.0",
        status=AssistantStatus.REFERENCE_ONLY,
        commands=("cn",),
        capabilities=frozenset({"code_review", "ci_checks", "reference"}),
        free_entry_path="Repository remains available as open-source reference code.",
        inference_may_cost=True,
        notes="Upstream repository is read-only; do not make it a new critical dependency.",
    ),
    AssistantSpec(
        assistant_id="roo_code",
        name="Roo Code",
        upstream="https://github.com/RooCodeInc/Roo-Code",
        license="Apache-2.0",
        status=AssistantStatus.RETIRED,
        commands=(),
        capabilities=frozenset({"reference"}),
        free_entry_path="Historical source only.",
        inference_may_cost=True,
        notes="Official extension was shut down in May 2026; excluded from active routing.",
    ),
)


def active_assistants() -> tuple[AssistantSpec, ...]:
    """Return assistants approved for local discovery and development routing."""
    return tuple(item for item in ASSISTANTS if item.status is AssistantStatus.ACTIVE)


def get_assistant(assistant_id: str) -> AssistantSpec:
    """Return one assistant spec or raise ``KeyError`` for an unknown id."""
    for item in ASSISTANTS:
        if item.assistant_id == assistant_id:
            return item
    raise KeyError(assistant_id)
