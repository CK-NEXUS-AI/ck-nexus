import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations" / "n8n"
POLICY = BASE / "agent-policy.json"
WORKFLOW = BASE / "ck-nexus-development-agent-fabric.workflow.json"
SUPER = BASE / "ck-nexus-super-agent-fabric.v2.workflow.json"
SKILLS = BASE / "skill-registry.json"
EVAL = BASE / "evaluation-policy.json"
TOOLS = BASE / "tool-registry.json"
MEMORY = BASE / "memory-policy.json"
RECOVERY = BASE / "recovery-policy.json"
MISSION_SCHEMA = BASE / "mission-contract.schema.json"
SIDECAR = BASE / "ck_nexus_agent_sidecar.mjs"


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


def test_tool_memory_and_recovery_policies_remain_bounded() -> None:
    tools = json.loads(TOOLS.read_text(encoding="utf-8"))
    memory = json.loads(MEMORY.read_text(encoding="utf-8"))
    recovery = json.loads(RECOVERY.read_text(encoding="utf-8"))
    assert tools["rules"]["external_write_default"] == "deny"
    assert "production_deployer" in tools["blocked_tools"]
    assert memory["write_rules"]["raw_secret_storage"] is False
    assert memory["checkpoint"]["resume_requires_policy_recheck"] is True
    assert "policy_denied" in recovery["non_retryable_failures"]
    assert recovery["circuit_breaker"]["production_mutation_attempt_opens_immediately"] is True


def test_mission_contract_denies_production_capabilities() -> None:
    schema = json.loads(MISSION_SCHEMA.read_text(encoding="utf-8"))
    constraints = schema["properties"]["constraints"]["properties"]
    assert constraints["allow_production_mutation"]["const"] is False
    assert constraints["allow_secret_export"]["const"] is False
    assert constraints["allow_merge"]["const"] is False
    assert constraints["allow_deploy"]["const"] is False
    assert schema["properties"]["branch"]["pattern"].startswith("^")


def test_sidecar_is_local_first_and_cannot_self_promote() -> None:
    text = SIDECAR.read_text(encoding="utf-8")
    assert "127.0.0.1" in text
    assert "release/q10-q16-closure" in text
    assert "production_mutation_denied" in text
    assert "secret_export_denied" in text
    assert "q10_promotion_allowed: false" in text
    assert "CK_NEXUS_INTELLIGENCE_ENDPOINT" in text
    assert "PROPOSAL_ONLY" in text
