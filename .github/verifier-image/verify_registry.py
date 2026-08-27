#!/usr/bin/env python3
"""Independent, image-baked verifier for CK-NEXUS registry governance changes.

This module is copied into the trusted verifier image. It deliberately does not
import or trust the registry validator shipped by the subject under test.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]*@sha256:[0-9a-f]{64}$")
MATURITY_ORDER = {
    "M0_MISSING": 0,
    "M1_CANDIDATE": 1,
    "M2_IMPLEMENTED_PARTIAL": 2,
    "M3_MEASURED": 3,
    "M4_INDEPENDENTLY_VERIFIED": 4,
    "M5_ADOPTED_CANONICAL": 5,
    "M6_PRODUCTION_QUALIFIED": 6,
}
MEASUREMENT_KINDS = {"GITHUB_ACTIONS", "LIVE_RUNTIME", "BENCHMARK", "TEST_RUN"}
INDEX_PATH = PurePosixPath("config/master_capability_evidence_registry.v1.json")
ALLOWED_EXACT_PATHS = {
    str(INDEX_PATH),
    "scripts/validate_master_capability_evidence_registry.py",
    "scripts/verify_master_registry_github_evidence.py",
    "tests/test_master_capability_evidence_registry.py",
    "docs/MASTER_CAPABILITY_EVIDENCE_REGISTRY.md",
    ".github/workflows/validate-registry.yml",
}
FRAGMENT_PREFIX = "config/master-capability-evidence/"
FORBIDDEN_WORKFLOW_MARKERS = (
    "pull_request_target",
    "write-all",
    "contents: write",
    "actions: write",
    "packages: write",
    "id-token: write",
    "deployments: write",
    "issues: write",
    "pull-requests: write",
    "secrets.",
    "--privileged",
    "docker.sock",
    "sudo ",
    "curl ",
    "wget ",
)
REQUIRED_WORKFLOW_MARKERS = (
    "contents: read",
    "actions: read",
    "python scripts/validate_master_capability_evidence_registry.py",
    "python -m scripts.verify_master_registry_github_evidence",
    "python -m pytest tests/test_master_capability_evidence_registry.py",
    "Assert non-authoritative boundary",
)


class RegistryVerificationError(RuntimeError):
    """Fail-closed registry verification error."""


def _canonical_digest(records: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_resolve(root: Path, raw_path: str) -> Path:
    logical = PurePosixPath(raw_path)
    if not raw_path or logical.is_absolute() or ".." in logical.parts:
        raise RegistryVerificationError(f"unsafe fragment path: {raw_path}")
    candidate = root.joinpath(*logical.parts)
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise RegistryVerificationError(f"fragment escapes workspace: {raw_path}")
    if candidate.is_symlink():
        raise RegistryVerificationError(f"fragment symlink is forbidden: {raw_path}")
    return candidate


def _load_registry(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index_file = root.joinpath(*INDEX_PATH.parts)
    if not index_file.is_file() or index_file.is_symlink():
        raise RegistryVerificationError("registry index missing or symlinked")
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryVerificationError(f"registry index unreadable: {exc}") from exc

    fragments = index.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        raise RegistryVerificationError("fragments must be a non-empty list")

    records: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for fragment in fragments:
        if not isinstance(fragment, dict):
            raise RegistryVerificationError("fragment entry must be an object")
        raw_path = str(fragment.get("path", ""))
        if raw_path in seen_paths:
            raise RegistryVerificationError(f"duplicate fragment path: {raw_path}")
        seen_paths.add(raw_path)
        file_path = _safe_resolve(root, raw_path)
        raw = file_path.read_bytes()
        expected_digest = str(fragment.get("sha256", ""))
        if not SHA256_RE.fullmatch(expected_digest):
            raise RegistryVerificationError(f"invalid fragment digest: {raw_path}")
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            raise RegistryVerificationError(f"fragment digest mismatch: {raw_path}")
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RegistryVerificationError(
                f"fragment JSON invalid: {raw_path}: {exc}"
            ) from exc
        if not isinstance(items, list):
            raise RegistryVerificationError(f"fragment must be a list: {raw_path}")
        if fragment.get("count") != len(items):
            raise RegistryVerificationError(f"fragment count mismatch: {raw_path}")
        records.extend(items)

    if index.get("record_count") != len(records):
        raise RegistryVerificationError("record_count mismatch")
    expected_records_digest = str(index.get("records_digest_sha256", ""))
    if not SHA256_RE.fullmatch(expected_records_digest):
        raise RegistryVerificationError("records digest format invalid")
    if _canonical_digest(records) != expected_records_digest:
        raise RegistryVerificationError("combined records digest mismatch")
    return index, records


def _has_subject_evidence(
    record: dict[str, Any],
    kind: str,
    status: str,
) -> bool:
    subject = record.get("sha")
    return isinstance(subject, str) and any(
        isinstance(evidence, dict)
        and evidence.get("kind") == kind
        and evidence.get("status") == status
        and evidence.get("subject_sha") == subject
        for evidence in record.get("evidence", [])
    )


def _has_measurement(record: dict[str, Any]) -> bool:
    return any(
        isinstance(evidence, dict)
        and evidence.get("kind") in MEASUREMENT_KINDS
        and evidence.get("status") == "SUCCESS"
        for evidence in record.get("evidence", [])
    )


def _validate_semantics(index: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if index.get("kind") != "NON_AUTHORITATIVE_RECONCILIATION_PROJECTION":
        raise RegistryVerificationError("registry must remain non-authoritative")
    authority = index.get("authority")
    if not isinstance(authority, dict):
        raise RegistryVerificationError("authority block missing")
    if authority.get("registry_can_issue_verified") is not False:
        raise RegistryVerificationError("registry cannot issue VERIFIED")
    if authority.get("registry_can_mutate_production") is not False:
        raise RegistryVerificationError("registry cannot mutate Production")
    if authority.get("chat_is_authority") is not False:
        raise RegistryVerificationError("chat cannot be authority")

    baseline = index.get("baseline")
    if not isinstance(baseline, dict):
        raise RegistryVerificationError("baseline block missing")
    baseline_sha = str(baseline.get("sha", ""))
    baseline_tree = str(baseline.get("tree", ""))
    if not SHA1_RE.fullmatch(baseline_sha) or not SHA1_RE.fullmatch(baseline_tree):
        raise RegistryVerificationError("baseline commit/tree must be exact Git SHA")

    seen: set[str] = set()
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise RegistryVerificationError(f"record {position} must be an object")
        rid = str(record.get("id", ""))
        if not rid or rid in seen:
            raise RegistryVerificationError(f"record id missing/duplicate: {rid}")
        seen.add(rid)
        maturity = str(record.get("maturity", ""))
        if maturity not in MATURITY_ORDER:
            raise RegistryVerificationError(f"{rid}: invalid maturity")
        source = record.get("source")
        adopted = bool(record.get("adopted", False))
        production = bool(record.get("production", False))
        sha = record.get("sha")
        if sha is not None and not SHA1_RE.fullmatch(str(sha)):
            raise RegistryVerificationError(f"{rid}: subject sha invalid")
        if source in {"DEV_PR", "RESEARCH_PR", "CHAT_CONTEXT"} and adopted:
            raise RegistryVerificationError(f"{rid}: noncanonical source claims adoption")
        if source == "CHAT_CONTEXT" and MATURITY_ORDER[maturity] > 1:
            raise RegistryVerificationError(f"{rid}: chat exceeds M1")
        if source == "RESEARCH_PR" and MATURITY_ORDER[maturity] > 1:
            raise RegistryVerificationError(f"{rid}: research PR exceeds M1")

        if maturity == "M3_MEASURED":
            if record.get("verification") != "MEASURED_NOT_VERIFIED":
                raise RegistryVerificationError(f"{rid}: M3 truth ceiling violated")
            if not isinstance(sha, str) or not SHA1_RE.fullmatch(sha):
                raise RegistryVerificationError(f"{rid}: M3 exact subject missing")
            if not _has_measurement(record):
                raise RegistryVerificationError(f"{rid}: M3 measurement missing")

        if maturity == "M4_INDEPENDENTLY_VERIFIED":
            if record.get("verification") != "INDEPENDENTLY_VERIFIED":
                raise RegistryVerificationError(f"{rid}: M4 verification state invalid")
            if not _has_subject_evidence(record, "INDEPENDENT_VERIFIER", "SUCCESS"):
                raise RegistryVerificationError(f"{rid}: M4 exact verifier receipt missing")

        if maturity == "M5_ADOPTED_CANONICAL":
            if not adopted:
                raise RegistryVerificationError(f"{rid}: M5 requires adopted=true")
            legacy_baseline = (
                source == "CANONICAL_MAIN"
                and record.get("verification") == "CANONICAL_PRESENT"
                and (sha is None or sha == baseline_sha)
            )
            if not legacy_baseline and not _has_subject_evidence(
                record, "INDEPENDENT_VERIFIER", "SUCCESS"
            ):
                raise RegistryVerificationError(
                    f"{rid}: non-baseline M5 independent receipt missing"
                )

        if record.get("truth") == "VERIFIED" and not _has_subject_evidence(
            record, "INDEPENDENT_VERIFIER", "SUCCESS"
        ):
            raise RegistryVerificationError(f"{rid}: VERIFIED without exact verifier receipt")

        if production or maturity == "M6_PRODUCTION_QUALIFIED":
            if maturity != "M6_PRODUCTION_QUALIFIED" or not adopted:
                raise RegistryVerificationError(f"{rid}: Production maturity/adoption invalid")
            if record.get("verification") != "INDEPENDENTLY_VERIFIED":
                raise RegistryVerificationError(f"{rid}: Production verifier state invalid")
            if not _has_subject_evidence(record, "INDEPENDENT_VERIFIER", "SUCCESS"):
                raise RegistryVerificationError(f"{rid}: Production verifier receipt missing")
            if not _has_subject_evidence(record, "PRODUCTION_GATE", "SUCCESS"):
                raise RegistryVerificationError(f"{rid}: Production gate receipt missing")


def _changed_paths(root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "HEAD", "--"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    if result.returncode != 0:
        raise RegistryVerificationError("unable to enumerate subject patch paths")
    paths = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    if not paths:
        raise RegistryVerificationError("registry governance profile requires a non-empty patch")
    return paths


def _validate_changed_paths(paths: tuple[str, ...]) -> None:
    for path in paths:
        if path in ALLOWED_EXACT_PATHS:
            continue
        if path.startswith(FRAGMENT_PREFIX) and path.endswith(".json"):
            continue
        raise RegistryVerificationError(f"out-of-scope changed path: {path}")


def _validate_workflow(root: Path) -> None:
    workflow = root / ".github/workflows/validate-registry.yml"
    if not workflow.is_file() or workflow.is_symlink():
        raise RegistryVerificationError("registry validation workflow missing or symlinked")
    text = workflow.read_text(encoding="utf-8")
    lowered = text.lower()
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in lowered:
            raise RegistryVerificationError(f"forbidden workflow marker: {marker}")
    for marker in REQUIRED_WORKFLOW_MARKERS:
        if marker not in text:
            raise RegistryVerificationError(f"required workflow marker missing: {marker}")


def _diff_digest(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--binary", "HEAD", "--"],
        check=False,
        capture_output=True,
        timeout=30,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    if result.returncode != 0:
        raise RegistryVerificationError("unable to digest subject patch")
    return hashlib.sha256(result.stdout).hexdigest()


def verify(workspace: Path) -> dict[str, Any]:
    root = workspace.resolve()
    if not root.is_dir() or not (root / ".git").exists():
        raise RegistryVerificationError("workspace must be a Git repository root")
    target_sha = os.environ.get("CKNEXUS_TARGET_SHA", "")
    if not SHA1_RE.fullmatch(target_sha):
        raise RegistryVerificationError("CKNEXUS_TARGET_SHA must be exact lowercase Git SHA")

    paths = _changed_paths(root)
    _validate_changed_paths(paths)
    index, records = _load_registry(root)
    _validate_semantics(index, records)
    _validate_workflow(root)

    logic_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "kind": "CKNEXUS_REGISTRY_GOVERNANCE_MACHINE_CHECK",
        "verification_profile": "registry_governance",
        "target_sha": target_sha,
        "registry_digest": index["records_digest_sha256"],
        "record_count": len(records),
        "changed_paths": list(paths),
        "subject_patch_sha256": _diff_digest(root),
        "verifier_logic_sha256": logic_digest,
        "network_required": False,
        "credentials_required": False,
        "external_measurement_binding_required": True,
        "verification_authority": False,
        "canonical_adoption": False,
        "production_mutation": False,
        "production_status": "NO-GO",
        "result": "MACHINE_CHECK_PASSED",
    }


def main() -> int:
    try:
        receipt = verify(Path("/workspace"))
    except (OSError, ValueError, RegistryVerificationError, subprocess.SubprocessError) as exc:
        print(f"REGISTRY_GOVERNANCE_VERIFY_ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
