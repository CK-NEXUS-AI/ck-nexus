from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "spiffe": ROOT / "schemas/spiffe_agent_identity_profile.schema.json",
    "otel": ROOT / "schemas/otel_agent_evidence_profile.schema.json",
    "nist": ROOT / "schemas/nist_agent_standards_tracker.schema.json",
}


def load(name):
    with SCHEMAS[name].open(encoding="utf-8") as handle:
        return json.load(handle)


def test_research_control_schemas_are_closed_contracts():
    for schema in SCHEMAS.values():
        data = json.loads(schema.read_text(encoding="utf-8"))
        assert data["$schema"].endswith("/draft/2020-12/schema")
        assert data["type"] == "object"
        assert data["additionalProperties"] is False
        assert data["required"]


def test_spiffe_profile_has_fail_closed_identity_states():
    schema = load("spiffe")
    assert set(schema["properties"]["attestation"]["enum"]) == {
        "VERIFIED",
        "FAILED",
        "UNKNOWN",
        "EXPIRED",
    }
    assert "identity_status" in schema["required"]
    assert "spiffe_id" in schema["required"]


def test_otel_profile_cannot_become_verification_authority():
    schema = load("otel")
    assert "telemetry_integrity" in schema["required"]
    assert "VERIFIED" in schema["properties"]["telemetry_integrity"]["enum"]
    assert "evidence_id" in schema["properties"]
    assert "verification_decision" not in schema["properties"]


def test_nist_tracker_separates_mapping_from_verification():
    schema = load("nist")
    statuses = set(schema["properties"]["ck_control_status"]["enum"])
    assert {"OBSERVED", "MAPPED", "IMPLEMENTED", "VERIFIED"} <= statuses


def test_profiles_contain_no_secret_bearing_fields():
    forbidden = {"api_key", "access_token", "refresh_token", "client_secret", "private_key"}
    for name in SCHEMAS:
        properties = set(load(name)["properties"])
        assert properties.isdisjoint(forbidden)
