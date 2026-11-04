#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

VERIFIERS = {
    "verify/q11-final-subject": {
        "workflow_file": "verify-q11-final-subject.yml",
        "workflow_name": "Verify Q11 final release subject",
    },
    "verify/q12-final-subject": {
        "workflow_file": "verify-q12-final-subject.yml",
        "workflow_name": "Verify Q12 final release subject on delegated self-hosted Linux",
    },
}


def request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-canonical-verifier-handoff",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status == 204:
            return {}
        return json.load(response)


def request_bytes(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-canonical-verifier-handoff",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def workflow_runs(
    *, repository: str, token: str, workflow_file: str, branch: str
) -> list[dict[str, Any]]:
    encoded_branch = urllib.parse.quote(branch, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_file}/runs?branch={encoded_branch}&event=workflow_dispatch&per_page=100"
    )
    return list(request_json(url, token).get("workflow_runs", []))


def dispatch(
    *, repository: str, token: str, workflow_file: str, branch: str
) -> None:
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_file}/dispatches"
    )
    request_json(url, token, method="POST", payload={"ref": branch})


def wait_for_new_run(
    *,
    repository: str,
    token: str,
    workflow_file: str,
    branch: str,
    previous_ids: set[int],
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    selected: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        runs = workflow_runs(
            repository=repository,
            token=token,
            workflow_file=workflow_file,
            branch=branch,
        )
        fresh = [run for run in runs if int(run.get("id", 0)) not in previous_ids]
        if fresh:
            selected = sorted(
                fresh,
                key=lambda item: int(item.get("id", 0)),
                reverse=True,
            )[0]
            if selected.get("status") == "completed":
                return selected
        time.sleep(10)
    if selected is None:
        raise TimeoutError("workflow dispatch created no observable run")
    raise TimeoutError(
        f"workflow run {selected.get('id')} did not complete before timeout"
    )


def find_artifact(
    *, repository: str, token: str, run_id: int, prefix: str
) -> dict[str, Any]:
    url = (
        f"https://api.github.com/repos/{repository}/actions/runs/"
        f"{run_id}/artifacts?per_page=100"
    )
    payload = request_json(url, token)
    artifacts = [
        item
        for item in payload.get("artifacts", [])
        if str(item.get("name", "")).startswith(prefix)
        and item.get("expired") is False
    ]
    if len(artifacts) != 1:
        raise ValueError(
            f"expected one non-expired artifact with prefix {prefix!r}, got {len(artifacts)}"
        )
    return artifacts[0]


def extract_evidence(archive: bytes, evidence_name: str) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        matches = [name for name in bundle.namelist() if Path(name).name == evidence_name]
        if len(matches) != 1:
            raise ValueError(
                f"expected one {evidence_name} in artifact, got {len(matches)}"
            )
        payload = json.loads(bundle.read(matches[0]).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence payload must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dispatch a canonical verifier workflow and normalize its GitHub artifact provenance"
        )
    )
    parser.add_argument("--branch", required=True, choices=sorted(VERIFIERS))
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--evidence-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "spinlnw10-art/ck-nexus")
    token = os.environ.get("GITHUB_TOKEN", "")
    config = VERIFIERS[args.branch]
    result: dict[str, Any] = {
        "result": "BLOCKED",
        "branch": args.branch,
        "workflow": config["workflow_name"],
        "errors": [],
    }
    try:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        before = workflow_runs(
            repository=repository,
            token=token,
            workflow_file=config["workflow_file"],
            branch=args.branch,
        )
        previous_ids = {int(run["id"]) for run in before}
        dispatch(
            repository=repository,
            token=token,
            workflow_file=config["workflow_file"],
            branch=args.branch,
        )
        run = wait_for_new_run(
            repository=repository,
            token=token,
            workflow_file=config["workflow_file"],
            branch=args.branch,
            previous_ids=previous_ids,
            timeout_seconds=args.timeout_seconds,
        )
        run_id = int(run["id"])
        if run.get("conclusion") != "success":
            raise ValueError(
                f"canonical verifier concluded {run.get('conclusion')!r} for run {run_id}"
            )
        artifact = find_artifact(
            repository=repository,
            token=token,
            run_id=run_id,
            prefix=args.artifact_prefix,
        )
        artifact_id = int(artifact["id"])
        digest = artifact.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError("GitHub artifact digest is missing or invalid")
        archive = request_bytes(
            f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip",
            token,
        )
        evidence = extract_evidence(archive, args.evidence_name)
        existing_run_id = evidence.get("github_run_id")
        if existing_run_id is not None and existing_run_id != run_id:
            raise ValueError("evidence github_run_id does not match canonical workflow run")
        evidence["github_run_id"] = run_id
        evidence["artifact_id"] = artifact_id
        evidence["artifact_digest"] = digest
        evidence["canonical_verifier_branch"] = args.branch
        evidence["canonical_verifier_head_sha"] = run.get("head_sha")
        result = evidence
    except (
        OSError,
        ValueError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
