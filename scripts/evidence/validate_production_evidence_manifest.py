#!/usr/bin/env python3
"""Fail-closed CK-NEXUS production evidence manifest validator.

This tool deliberately derives reconciliation state from evidence. It never
accepts a human/agent-authored ready_for_q16_final_package flag as authority.
JSON Schema validation is used when the optional jsonschema package is present;
semantic validation is always performed with the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_ORDER = ["Q10", "Q11", "Q12"]


def _is_hex(value: Any, pattern: re.Pattern[str]) -> bool:
    return isinstance(value, str) and bool(pattern.fullmatch(value))


def _canonical_bytes_without_integrity(manifest: dict[str, Any]) -> bytes:
    # This is deterministic JSON for local integrity checks. The manifest contract
    # names RFC8785 JCS; final signing must use an RFC8785 implementation.
    payload = {key: value for key, value in manifest.items() if key != "manifest_integrity"}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def derive(manifest: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    frozen = manifest.get("frozen_production_subject", {})
    gates = manifest.get("gates", [])

    if [gate.get("gate") for gate in gates] != EXPECTED_ORDER:
        errors.append("gate order must be exactly Q10,Q11,Q12")

    frozen_commit = frozen.get("tested_commit")
    frozen_tree = frozen.get("tested_tree")
    if not _is_hex(frozen_commit, HEX40):
        errors.append("frozen tested_commit must be 40 lowercase hex characters")
    if not _is_hex(frozen_tree, HEX40):
        errors.append("frozen tested_tree must be 40 lowercase hex characters")

    all_pass = len(gates) == 3 and all(gate.get("result") == "PASS" for gate in gates)
    same_commit = len(gates) == 3 and all(
        gate.get("tested_commit") == frozen_commit for gate in gates
    )
    same_tree = len(gates) == 3 and all(gate.get("tested_tree") == frozen_tree for gate in gates)

    no_mutation = len(gates) == 3
    artifact_digests = len(gates) == 3
    tooling_pinned = len(gates) == 3
    workflows_pinned = len(gates) == 3

    for gate in gates:
        name = gate.get("gate", "UNKNOWN")
        mutation = gate.get("subject_mutation_check", {})
        mutation_ok = (
            mutation.get("expected_commit") == frozen_commit
            and mutation.get("expected_tree") == frozen_tree
            and mutation.get("observed_commit_before") == frozen_commit
            and mutation.get("observed_commit_after") == frozen_commit
            and mutation.get("observed_tree_before") == frozen_tree
            and mutation.get("observed_tree_after") == frozen_tree
            and mutation.get("mutation_detected") is False
            and mutation.get("check_result") == "PASS"
        )
        no_mutation = no_mutation and mutation_ok

        artifact_digests = artifact_digests and _is_hex(gate.get("artifact_sha256"), HEX64)
        artifact_digests = artifact_digests and _is_hex(
            gate.get("evidence_bundle_sha256"), HEX64
        )

        if name in {"Q11", "Q12"}:
            tooling_pinned = tooling_pinned and _is_hex(gate.get("tooling_commit"), HEX40)
            tooling_pinned = tooling_pinned and _is_hex(
                gate.get("tooling_entrypoint_sha256"), HEX64
            )
            workflows_pinned = workflows_pinned and bool(gate.get("workflow_path"))
            workflows_pinned = workflows_pinned and _is_hex(
                gate.get("workflow_definition_sha256"), HEX64
            )
        elif name == "Q10":
            executor = gate.get("executor", {})
            tooling_pinned = tooling_pinned and executor.get("name") == (
                "Codex Security Deep Security Scan"
            )
            tooling_pinned = tooling_pinned and bool(executor.get("scan_id"))

    chain_verified = False
    if len(gates) == 3:
        q10, q11, q12 = gates
        q10_hash = q10.get("evidence_bundle_sha256")
        q11_hash = q11.get("evidence_bundle_sha256")
        chain_verified = (
            _is_hex(q10_hash, HEX64)
            and _is_hex(q11_hash, HEX64)
            and q11.get("previous_gate_evidence_sha256") == q10_hash
            and q12.get("previous_gate_evidence_sha256") == q11_hash
        )

    independent = manifest.get("independent_verification", {})
    independent_complete = (
        independent.get("result") == "PASS"
        and bool(independent.get("verifier_id"))
        and _is_hex(independent.get("report_sha256"), HEX64)
        and _is_hex(independent.get("verified_manifest_payload_sha256"), HEX64)
    )

    derived = {
        "all_gates_pass": all_pass,
        "all_gates_share_tested_commit": same_commit,
        "all_gates_share_tested_tree": same_tree,
        "no_subject_mutation_across_gates": no_mutation,
        "tooling_commits_are_pinned": tooling_pinned,
        "workflow_definitions_pinned": workflows_pinned,
        "artifact_digests_verified": artifact_digests,
        "evidence_chain_verified": chain_verified,
        "independent_verifier_complete": independent_complete,
    }
    derived["ready_for_q16_final_package"] = all(derived.values())

    q12 = next((gate for gate in gates if gate.get("gate") == "Q12"), None)
    if q12 and q12.get("result") == "PASS":
        enforcement = q12.get("q12_enforcement", {})
        if not all(enforcement.get(key) is True for key in enforcement):
            errors.append("Q12 PASS requires every q12_enforcement field to be true")

    q11 = next((gate for gate in gates if gate.get("gate") == "Q11"), None)
    if q11 and q11.get("result") == "PASS":
        provider = q11.get("provider_execution", {})
        if provider.get("credential_value_recorded") is not False:
            errors.append("Q11 credential_value_recorded must be false")
        if provider.get("live_network_call") is not True:
            errors.append("Q11 PASS requires live_network_call=true")

    recorded = manifest.get("reconciliation_gate", {})
    for key, expected in derived.items():
        actual = recorded.get(key)
        if actual is not None and actual is not expected:
            errors.append(f"recorded {key}={actual!r} disagrees with derived {expected!r}")

    return derived, errors


def validate_schema_if_available(
    manifest: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError:
        return []
    validator = jsonschema.Draft202012Validator(schema)
    return [f"schema: {error.message}" for error in validator.iter_errors(manifest)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--require-final", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    if args.schema:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
        errors.extend(validate_schema_if_available(manifest, schema))

    derived, semantic_errors = derive(manifest)
    errors.extend(semantic_errors)

    integrity = manifest.get("manifest_integrity", {})
    local_digest = hashlib.sha256(_canonical_bytes_without_integrity(manifest)).hexdigest()
    recorded_digest = integrity.get("payload_sha256")
    if recorded_digest is not None and recorded_digest != local_digest:
        errors.append("manifest payload_sha256 does not match deterministic local payload digest")

    if args.require_final and not derived["ready_for_q16_final_package"]:
        errors.append("manifest is not eligible for Q16 final package")

    print(json.dumps({"derived": derived, "errors": errors}, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
