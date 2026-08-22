import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "integrations" / "n8n" / "agent-policy.json"
WORKFLOW = ROOT / "integrations" / "n8n" / "ck-nexus-development-agent-fabric.workflow.json"


def test_policy_protects_production_subject_and_pr14() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["mode"] == "development_only"
    assert "main" in policy["protected_refs"]
    assert "release/q10-q16-closure" in policy["protected_refs"]
    assert 14 in policy["protected_pull_requests"]
    assert "merge_pull_request" in policy["denied_actions"]
    assert "deploy_production" in policy["denied_actions"]
    assert "read_raw_secrets" in policy["denied_actions"]


def test_workflow_is_development_only_and_secret_free() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    text = WORKFLOW.read_text(encoding="utf-8")
    assert workflow["active"] is False
    assert "CK_NEXUS_AGENT_ENDPOINT" in text
    assert "production_mutation:false" in text
    assert "raw_secret_access:false" in text
    assert "release/q10-q16-closure" in text
    assert "pull_request ?? 0) === 14" in text
    lowered = text.lower()
    assert "sk-proj-" not in lowered
    assert "api_key=" not in lowered
    assert "password=" not in lowered
