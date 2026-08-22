import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "integrations" / "n8n" / "agent-policy.json"
WORKFLOW = ROOT / "integrations" / "n8n" / "ck-nexus-development-agent-fabric.workflow.json"
SUPER = ROOT / "integrations" / "n8n" / "ck-nexus-super-agent-fabric.v2.workflow.json"
SKILLS = ROOT / "integrations" / "n8n" / "skill-registry.json"
EVAL = ROOT / "integrations" / "n8n" / "evaluation-policy.json"
SIDECAR = ROOT / "integrations" / "n8n" / "ck_nexus_agent_sidecar.mjs"


def test_policy_protects_production_subject_and_pr14() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["mode"] == "development_only"
    assert "main" in policy["protected_refs"]
    assert "release/q10-q16-closure" in policy["protected_refs"]
    assert 14 in policy["protected_pull_requests"]
    assert "merge_pull_request" in policy["denied_actions"]
    assert "deploy_production" in policy["denied_actions"]
    assert "read_raw_secrets" in policy["denied_actions"]


def _assert_workflow_secret_free(path: Path) -> None:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    assert workflow["active"] is False
    assert "CK_NEXUS_AGENT_ENDPOINT" in text
    assert "production_mutation" in text
    assert "release/q10-q16-closure" in text
    lowered = text.lower()
    assert "sk-proj-" not in lowered
    assert "api_key=" not in lowered
    assert "password=" not in lowered


def test_workflows_are_development_only_and_secret_free() -> None:
    _assert_workflow_secret_free(WORKFLOW)
    _assert_workflow_secret_free(SUPER)


def test_super_agent_has_independent_review_stage() -> None:
    workflow = json.loads(SUPER.read_text(encoding="utf-8"))
    names = {node["name"] for node in workflow["nodes"]}
    assert "Candidate Council" in names
    assert "Independent Review Compiler" in names
    assert "Independent Review Adapter" in names
    assert "Final Development Gate" in names
    text = SUPER.read_text(encoding="utf-8")
    assert "VERIFIED_DEVELOPMENT_CANDIDATE" in text
    assert "production_ready:false" in text
    assert "q10_q11_q12_evidence:false" in text


def test_skill_registry_and_evaluation_policy_are_fail_closed() -> None:
    skills = json.loads(SKILLS.read_text(encoding="utf-8"))
    evaluation = json.loads(EVAL.read_text(encoding="utf-8"))
    assert "production_deploy" in skills["forbidden_skills"]
    assert "secret_exfiltration" in skills["forbidden_skills"]
    assert evaluation["minimum_score_for_development_candidate"] >= 0.8
    assert "raw_secret_present" in evaluation["hard_fail_conditions"]
    assert "verifier_missing" in evaluation["hard_fail_conditions"]


def test_sidecar_is_local_first_and_cannot_self_promote() -> None:
    text = SIDECAR.read_text(encoding="utf-8")
    assert "127.0.0.1" in text
    assert "release/q10-q16-closure" in text
    assert "production_mutation_denied" in text
    assert "secret_export_denied" in text
    assert "q10_promotion_allowed: false" in text
    assert "CK_NEXUS_INTELLIGENCE_ENDPOINT" in text
    assert "PROPOSAL_ONLY" in text
