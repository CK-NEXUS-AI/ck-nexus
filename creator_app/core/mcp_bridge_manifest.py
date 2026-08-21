from __future__ import annotations

from pydantic import BaseModel, Field


class MCPBridgeManifest(BaseModel):
    module_id: str = "ck-nexus.chat-mcp-bridge"
    version: str = "1.0.0-dev"
    default_enabled: bool = False
    read_only: bool = True
    production_mutation_allowed: bool = False
    external_write_allowed: bool = False
    provider_sdk_required: bool = False
    supported_commands: list[str] = Field(
        default_factory=lambda: [
            "status",
            "memory.status",
            "swarm.status",
            "inspect",
            "verify",
            "explain",
        ]
    )
    required_runtime_contract: str = "gen6.3"
    requires_governor_approval: bool = True
    requires_verified_ci: bool = True
    requires_verified_evidence: bool = True


def build_manifest() -> MCPBridgeManifest:
    return MCPBridgeManifest()
