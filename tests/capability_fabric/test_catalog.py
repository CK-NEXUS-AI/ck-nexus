from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.capability_fabric.catalog import (
    ArtifactClass,
    ArtifactStatus,
    CapabilityArtifact,
    CapabilityCatalog,
)

CATALOG = "config/capability_catalog.json"


def test_catalog_keeps_tools_plugins_skills_and_workflows_distinct() -> None:
    catalog = CapabilityCatalog.load(CATALOG)
    assert catalog.get("n8n-workflows").artifact_class is ArtifactClass.WORKFLOW_ENGINE
    assert catalog.get("agnes-skills").artifact_class is ArtifactClass.SKILL
    assert catalog.get("open-vsx-ai-registry").artifact_class is ArtifactClass.PLUGIN
    assert catalog.get("connector-fabric").artifact_class is ArtifactClass.CONNECTOR
    assert catalog.get("mcp-runtime").artifact_class is ArtifactClass.TOOL
    assert catalog.get("litellm-gateway").artifact_class is ArtifactClass.AI_GATEWAY
    assert catalog.get("opensandbox-agent-sandbox-runtime").artifact_class is ArtifactClass.SANDBOX
    assert catalog.get("openai-agents-sdk").artifact_class is ArtifactClass.AGENT_FRAMEWORK


def test_external_artifacts_never_receive_core_authority() -> None:
    catalog = CapabilityCatalog.load(CATALOG)
    assert catalog.get("cknexus-core").authority_scope == "L3"
    assert all(
        item.authority_scope == "NONE"
        for item in catalog.list()
        if item.artifact_class is not ArtifactClass.CORE
    )


def test_discovery_candidates_are_not_installed_or_approved() -> None:
    catalog = CapabilityCatalog.load(CATALOG)
    assert catalog.get("docling").status is ArtifactStatus.DISCOVERY_ONLY
    assert catalog.get("ragflow").status is ArtifactStatus.DISCOVERY_ONLY
    assert catalog.get("activepieces").status is ArtifactStatus.DISCOVERY_ONLY


def test_catalog_rejects_external_l3_authority() -> None:
    with pytest.raises(ValueError, match="authority_scope=NONE"):
        CapabilityArtifact.from_mapping(
            {
                "id": "evil",
                "name": "External agent",
                "class": "agent_framework",
                "status": "present",
                "integration_point": "worker",
                "authority_scope": "L3",
            }
        )


def test_catalog_rejects_duplicate_ids(tmp_path) -> None:
    payload = json.loads(Path(CATALOG).read_text(encoding="utf-8"))
    payload["artifacts"].append(dict(payload["artifacts"][0]))
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        CapabilityCatalog.load(path)



def test_verification_state_is_exposed_as_read_only_metadata() -> None:
    catalog = CapabilityCatalog.load(CATALOG)
    artifact = catalog.get("promptfoo-evals-redteam")
    state = artifact.verification_state
    assert state is not None
    assert state.discovered is True
    assert state.available_in_chat_session is False
    assert state.online_verified is True
    assert state.not_connected is True
    assert state.not_integrated is True
    assert state.runtime_verified is False
    assert artifact.authority_scope == "NONE"


def test_catalog_rejects_inconsistent_verification_state() -> None:
    with pytest.raises(ValueError, match="runtime_verified requires connected and integrated"):
        CapabilityArtifact.from_mapping(
            {
                "id": "invalid-verification",
                "name": "Invalid verification",
                "class": "tool",
                "status": "discovery_only",
                "integration_point": "review-only",
                "authority_scope": "NONE",
                "verification_state": {
                    "discovered": True,
                    "available_in_chat_session": False,
                    "online_verified": True,
                    "not_connected": True,
                    "not_integrated": False,
                    "runtime_verified": True,
                },
            }
        )



def test_connection_and_integration_states_are_independent() -> None:
    connected_but_not_integrated = CapabilityArtifact.from_mapping(
        {
            "id": "connected-not-integrated",
            "name": "Connected but not integrated",
            "class": "connector",
            "status": "partial",
            "integration_point": "external service connection only",
            "authority_scope": "NONE",
            "verification_state": {
                "discovered": True,
                "available_in_chat_session": False,
                "online_verified": True,
                "not_connected": False,
                "not_integrated": True,
                "runtime_verified": False,
            },
        }
    )
    integrated_but_not_connected = CapabilityArtifact.from_mapping(
        {
            "id": "integrated-not-connected",
            "name": "Integrated but not connected",
            "class": "agent_framework",
            "status": "partial",
            "integration_point": "source adapter exists; no live service connection",
            "authority_scope": "NONE",
            "verification_state": {
                "discovered": True,
                "available_in_chat_session": False,
                "online_verified": True,
                "not_connected": True,
                "not_integrated": False,
                "runtime_verified": False,
            },
        }
    )
    assert connected_but_not_integrated.verification_state is not None
    assert connected_but_not_integrated.verification_state.not_connected is False
    assert connected_but_not_integrated.verification_state.not_integrated is True
    assert integrated_but_not_connected.verification_state is not None
    assert integrated_but_not_connected.verification_state.not_connected is True
    assert integrated_but_not_connected.verification_state.not_integrated is False


def test_openai_agents_sdk_is_partial_not_runtime_verified() -> None:
    artifact = CapabilityCatalog.load(CATALOG).get("openai-agents-sdk")
    assert artifact.artifact_class is ArtifactClass.AGENT_FRAMEWORK
    assert artifact.status is ArtifactStatus.PARTIAL
    assert artifact.authority_scope == "NONE"
    assert artifact.verification_state is not None
    assert artifact.verification_state.discovered is True
    assert artifact.verification_state.online_verified is True
    assert artifact.verification_state.not_connected is True
    assert artifact.verification_state.not_integrated is False
    assert artifact.verification_state.runtime_verified is False

def test_catalog_rejects_non_boolean_verification_state() -> None:
    with pytest.raises(ValueError, match="fields must be booleans"):
        CapabilityArtifact.from_mapping(
            {
                "id": "invalid-verification-type",
                "name": "Invalid verification type",
                "class": "tool",
                "status": "discovery_only",
                "integration_point": "review-only",
                "authority_scope": "NONE",
                "verification_state": {
                    "discovered": True,
                    "available_in_chat_session": False,
                    "online_verified": True,
                    "not_connected": True,
                    "not_integrated": True,
                    "runtime_verified": "false",
                },
            }
        )


def test_all_discovery_candidates_have_independent_verification_states() -> None:
    catalog = CapabilityCatalog.load(CATALOG)
    candidate_ids = (
        "agent-skills-standard",
        "promptfoo-evals-redteam",
        "inspect-ai-evals",
        "playwright-mcp",
        "official-mcp-registry",
        "opensandbox-agent-sandbox-runtime",
        "agentclash-agent-evaluation",
    )
    for artifact_id in candidate_ids:
        artifact = catalog.get(artifact_id)
        state = artifact.verification_state
        assert artifact.status is ArtifactStatus.DISCOVERY_ONLY
        assert artifact.authority_scope == "NONE"
        assert state is not None
        assert state.discovered is True
        assert state.available_in_chat_session is False
        assert state.online_verified is True
        assert state.not_connected is True
        assert state.not_integrated is True
        assert state.runtime_verified is False


def test_agentclash_remains_discovery_only_and_non_authoritative() -> None:
    artifact = CapabilityCatalog.load(CATALOG).get("agentclash-agent-evaluation")
    assert artifact.artifact_class is ArtifactClass.TOOL
    assert artifact.status is ArtifactStatus.DISCOVERY_ONLY
    assert artifact.authority_scope == "NONE"
    assert artifact.verification_state is not None
    assert artifact.verification_state.discovered is True
    assert artifact.verification_state.available_in_chat_session is False
    assert artifact.verification_state.online_verified is True
    assert artifact.verification_state.not_connected is True
    assert artifact.verification_state.not_integrated is True
    assert artifact.verification_state.runtime_verified is False
