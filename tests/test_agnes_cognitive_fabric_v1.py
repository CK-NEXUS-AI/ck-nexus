import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations" / "n8n"


def test_agnes_registry_is_fail_closed():
    data = json.loads((BASE / "agnes-fabric-registry.json").read_text(encoding="utf-8"))
    assert data["authority"] == "ck_nexus_governor"
    assert data["mode"] == "development_only"
    assert "production_deploy" in data["forbidden"]
    assert data["pressure_policy"]["CRITICAL"]["max_concurrency"] == 0
    assert data["resource_defaults"]["allow_browser"] is False


def test_agnes_runtime_contracts_present():
    text = (BASE / "agnes_fabric_runtime.mjs").read_text(encoding="utf-8")
    assert "selectCapabilities" in text
    assert "resourceAdmission" in text
    assert "saveCheckpoint" in text
    assert "loadCheckpoint" in text
    assert "traceEnvelope" in text
    assert "production_mutation:false" in text


def test_sidecar_v2_keeps_production_fail_closed():
    text = (BASE / "ck_nexus_agent_sidecar_v2.mjs").read_text(encoding="utf-8")
    assert "release/q10-q16-closure" in text
    assert "pr14_denied" in text
    assert "production_mutation_denied" in text
    assert "secret_export_denied" in text
    assert "resource_pressure_denied" in text
    assert "/v1/checkpoint" in text
    assert "buildAgnesContext" in text


def test_sidecar_v2_is_local_and_development_only():
    text = (BASE / "ck_nexus_agent_sidecar_v2.mjs").read_text(encoding="utf-8")
    assert "127.0.0.1" in text
    assert "development_only" in text
    assert "main" in text
    assert "q10_promotion_allowed:false" in text


def test_resource_guard_remains_non_production():
    text = (BASE / "adaptive_resource_guard.ps1").read_text(encoding="utf-8")
    assert "pressure_state" in text
    assert "recommended_concurrency" in text
    assert "production_mutation=$false" in text
    assert "FailOnCritical" in text
