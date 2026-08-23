from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CLAIM_ID_PATTERN = re.compile(r"^CLAIM-[A-Z0-9_]+-[0-9]{3}$")
SHA40_PATTERN = re.compile(r"^[a-f0-9]{40}$")
SHA64_PATTERN = re.compile(r"^[a-f0-9]{64}$")
VALID_STATES = {
    "TARGET",
    "MEASURED_NOT_VERIFIED",
    "VERIFIED",
    "REJECTED",
}
VALID_TRANSITIONS = {
    (None, "TARGET"),
    ("TARGET", "MEASURED_NOT_VERIFIED"),
    ("MEASURED_NOT_VERIFIED", "VERIFIED"),
    ("MEASURED_NOT_VERIFIED", "REJECTED"),
    ("VERIFIED", "REJECTED"),
    ("REJECTED", "MEASURED_NOT_VERIFIED"),
}


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("claim file must contain a JSON object")
    return data


def validate_claim(claim: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    claim_id = claim.get("claim_id")
    if not isinstance(claim_id, str) or not CLAIM_ID_PATTERN.fullmatch(claim_id):
        errors.append("claim_id is invalid")

    state = claim.get("state")
    if state not in VALID_STATES:
        errors.append("state is invalid")

    if not _non_empty(claim.get("claim_text_th")):
        errors.append("claim_text_th is required")
    if not _non_empty(claim.get("category")):
        errors.append("category is required")
    if not _non_empty(claim.get("created_by")):
        errors.append("created_by is required")

    subject = claim.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject is required")
    else:
        commit = subject.get("commit")
        if not isinstance(commit, str) or not SHA40_PATTERN.fullmatch(commit):
            errors.append("subject.commit must be a 40-character lowercase hex SHA")
        if not _non_empty(subject.get("component")):
            errors.append("subject.component is required")
        if not _non_empty(subject.get("environment")):
            errors.append("subject.environment is required")

    benchmark = claim.get("benchmark")
    evidence = claim.get("evidence")
    verifier = claim.get("verifier")

    if state != "TARGET":
        if not isinstance(benchmark, dict):
            errors.append("benchmark is required when state is not TARGET")
        else:
            runs = benchmark.get("runs")
            if not isinstance(runs, int) or runs < 3:
                errors.append("benchmark.runs must be at least 3")
            if benchmark.get("aggregation") not in {"median", "worst_case"}:
                errors.append("benchmark.aggregation must be median or worst_case")
            if not _non_empty(benchmark.get("measurement_method")):
                errors.append("benchmark.measurement_method is required")
            if not _non_empty(benchmark.get("measurement_limitations")):
                errors.append("benchmark.measurement_limitations is required")
        if not isinstance(evidence, dict):
            errors.append("evidence is required when state is not TARGET")
        else:
            digest = evidence.get("evidence_sha256")
            if not isinstance(digest, str) or not SHA64_PATTERN.fullmatch(digest):
                errors.append("evidence.evidence_sha256 must be a 64-character lowercase hex SHA")
            if not _non_empty(evidence.get("evidence_path")):
                errors.append("evidence.evidence_path is required")
            if not _non_empty(evidence.get("output_digest")):
                errors.append("evidence.output_digest is required")

    if state in {"VERIFIED", "REJECTED"}:
        if not isinstance(verifier, dict):
            errors.append("verifier is required for VERIFIED or REJECTED claims")
        else:
            verified_by = verifier.get("verified_by")
            if not _non_empty(verified_by):
                errors.append("verifier.verified_by is required")
            if verified_by == claim.get("created_by"):
                errors.append("self-certification is not allowed")
            if not _non_empty(verifier.get("verified_at")):
                errors.append("verifier.verified_at is required")
            if not _non_empty(verifier.get("verdict_reason")):
                errors.append("verifier.verdict_reason is required")

    history = claim.get("state_history")
    if not isinstance(history, list) or not history:
        errors.append("state_history must contain at least one entry")
    else:
        previous_to_state: str | None = None
        for index, entry in enumerate(history):
            if not isinstance(entry, dict):
                errors.append(f"state_history[{index}] must be an object")
                continue
            from_state = entry.get("from_state")
            to_state = entry.get("to_state")
            if (from_state, to_state) not in VALID_TRANSITIONS:
                errors.append(
                    f"state_history[{index}] has forbidden transition "
                    f"{from_state!r} -> {to_state!r}"
                )
            if index == 0 and (from_state, to_state) != (None, "TARGET"):
                errors.append("first state_history entry must create TARGET from null")
            if index > 0 and from_state != previous_to_state:
                errors.append(f"state_history[{index}] does not continue the prior state")
            if not _non_empty(entry.get("at")):
                errors.append(f"state_history[{index}].at is required")
            if not _non_empty(entry.get("reason")):
                errors.append(f"state_history[{index}].reason is required")
            previous_to_state = to_state
        if history and isinstance(history[-1], dict) and history[-1].get("to_state") != state:
            errors.append("state must equal the final state_history.to_state")

    return errors


def _load_from_git(base_ref: str, path: Path) -> dict[str, Any] | None:
    result = subprocess.run(
        ["git", "show", f"{base_ref}:{path.as_posix()}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("base claim must contain a JSON object")
    return data


def validate_append_only(current: dict[str, Any], previous: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if current.get("claim_id") != previous.get("claim_id"):
        errors.append("claim_id cannot change")
    old_history = previous.get("state_history")
    new_history = current.get("state_history")
    if not isinstance(old_history, list) or not isinstance(new_history, list):
        errors.append("state_history must remain a list")
        return errors
    if len(new_history) < len(old_history):
        errors.append("state_history is append-only and cannot shrink")
    elif new_history[: len(old_history)] != old_history:
        errors.append("existing state_history entries cannot be modified")
    return errors


def publication_status(claim: dict[str, Any], current_subject_commit: str | None) -> str:
    if claim.get("state") != "VERIFIED":
        return str(claim.get("state"))
    if current_subject_commit is None:
        return "VERIFIED"
    subject = claim.get("subject")
    if isinstance(subject, dict) and subject.get("commit") != current_subject_commit:
        return "STALE"
    return "VERIFIED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--base-ref")
    parser.add_argument("--current-subject-commit")
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        claim = _load(path)
        errors = validate_claim(claim)
        if args.base_ref:
            previous = _load_from_git(args.base_ref, path)
            if previous is not None:
                errors.extend(validate_append_only(claim, previous))
        status = publication_status(claim, args.current_subject_commit)
        if status == "STALE":
            errors.append("verified claim is stale for the supplied current subject commit")
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}")
        else:
            print(f"{path}: PASS state={claim['state']} publication_status={status}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
