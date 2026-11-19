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


def test_search_control_fabric_is_catalogued_without_authority():
    catalog = CapabilityCatalog.load(CATALOG)
    artifact = catalog.get("search-control-fabric")
    assert artifact.artifact_class is ArtifactClass.CONNECTOR
    assert artifact.status is ArtifactStatus.PARTIAL
    assert artifact.authority_scope == "NONE"
