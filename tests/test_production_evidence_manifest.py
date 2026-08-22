from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "evidence" / "validate_production_evidence_manifest.py"
TEMPLATE_PATH = ROOT / "evidence" / "templates" / "ck-nexus-evidence-manifest-template.v2.1.json"

spec = importlib.util.spec_from_file_location("production_manifest_validator", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def load_template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_pending_template_is_fail_closed() -> None:
    manifest = load_template()
    derived, errors = validator.derive(manifest)
    assert errors == []
    assert derived["all_gates_share_tested_commit"] is True
    assert derived["all_gates_share_tested_tree"] is True
    assert derived["all_gates_pass"] is False
    assert derived["tooling_commits_are_pinned"] is False
    assert derived["evidence_chain_verified"] is False
    assert derived["ready_for_q16_final_package"] is False


def test_subject_mismatch_never_becomes_ready() -> None:
    manifest = load_template()
    manifest["gates"][1]["tested_commit"] = "0" * 40
    derived, _ = validator.derive(manifest)
    assert derived["all_gates_share_tested_commit"] is False
    assert derived["ready_for_q16_final_package"] is False


def test_human_authored_ready_flag_cannot_override_derived_state() -> None:
    manifest = load_template()
    manifest["reconciliation_gate"]["ready_for_q16_final_package"] = True
    derived, errors = validator.derive(manifest)
    assert derived["ready_for_q16_final_package"] is False
    assert any("ready_for_q16_final_package" in error for error in errors)


def test_evidence_chain_is_ordered() -> None:
    manifest = load_template()
    digest_a = "a" * 64
    digest_b = "b" * 64
    manifest["gates"][0]["evidence_bundle_sha256"] = digest_a
    manifest["gates"][1]["evidence_bundle_sha256"] = digest_b
    manifest["gates"][1]["previous_gate_evidence_sha256"] = digest_a
    manifest["gates"][2]["previous_gate_evidence_sha256"] = digest_b
    derived, _ = validator.derive(manifest)
    assert derived["evidence_chain_verified"] is True

    swapped = deepcopy(manifest)
    swapped["gates"][2]["previous_gate_evidence_sha256"] = digest_a
    derived, _ = validator.derive(swapped)
    assert derived["evidence_chain_verified"] is False


def test_q12_pass_requires_all_enforcement_proofs() -> None:
    manifest = load_template()
    q12 = manifest["gates"][2]
    q12["result"] = "PASS"
    derived, errors = validator.derive(manifest)
    assert derived["all_gates_pass"] is False
    assert any("Q12 PASS requires" in error for error in errors)


def test_q11_pass_requires_live_network_call_and_no_secret_recording() -> None:
    manifest = load_template()
    q11 = manifest["gates"][1]
    q11["result"] = "PASS"
    q11["provider_execution"]["live_network_call"] = False
    _, errors = validator.derive(manifest)
    assert any("live_network_call=true" in error for error in errors)
    assert q11["provider_execution"]["credential_value_recorded"] is False
