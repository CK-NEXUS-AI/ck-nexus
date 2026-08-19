#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ALLOWED = {
    "verify/q11-final-subject": "Verify Q11 final release subject",
    "verify/q12-final-subject": "Verify Q12 final release subject on delegated self-hosted Linux",
}


def run_git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.stdout.strip()


def api_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-canonical-verifier-handoff",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def api_bytes(url: str, token: str) -> bytes:
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


def trigger(branch: str, message: str) -> str:
    if branch not in ALLOWED:
        raise ValueError(f"branch is not an allowed verifier branch: {branch}")
    run_git("fetch", "origin", f"refs/heads/{branch}")
    run_git("checkout", "--detach", "FETCH_HEAD")
    run_git("config", "user.name", "ck-nexus-closure-bot")
    run_git("config", "user.email", "ck-nexus-closure-bot@users.noreply.github.com")
    run_git("commit", "--allow-empty", "-m", message)
    sha = run_git("rev-parse", "HEAD")
    run_git("push", "origin", f"{sha}:refs/heads/{branch}")
    return sha


def wait_for_run(
    *, repository: str, token: str, sha: str, workflow_name: str, timeout_seconds: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    encoded_sha = urllib.parse.quote(sha, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/runs"
        f"?head_sha={encoded_sha}&per_page=100"
    )
    while time.monotonic() < deadline:
        payload = api_json(url, token)
        runs = payload.get("workflow_runs", [])
        matching = [run for run in runs if run.get("name") == workflow_name]
        if matching:
            run = sorted(matching, key=lambda item: int(item.get("id", 0)), reverse=True)[0]
            if run.get("status") == "completed":
                return run
        time.sleep(10)
    raise TimeoutError(f"timed out waiting for workflow: {workflow_name}")


def find_artifact(
    *, repository: str, token: str, run_id: int, prefix: str
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"
    payload = api_json(url, token)
    artifacts = [
        item
        for item in payload.get("artifacts", [])
        if str(item.get("name", "")).startswith(prefix) and item.get("expired") is False
    ]
    if len(artifacts) != 1:
        raise ValueError(f"expected one non-expired artifact with prefix {prefix!r}, got {len(artifacts)}")
    return artifacts[0]


def extract_evidence(archive: bytes, evidence_name: str) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        matches = [name for name in bundle.namelist() if Path(name).name == evidence_name]
        if len(matches) != 1:
            raise ValueError(f"expected one {evidence_name} in artifact, got {len(matches)}")
        raw = bundle.read(matches[0])
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence payload must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trigger canonical verifier branch and normalize its GitHub artifact provenance"
    )
    parser.add_argument("--branch", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--evidence-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--message", default="chore: canonical closure verifier handoff")
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "spinlnw10-art/ck-nexus")
    token = os.environ.get("GITHUB_TOKEN", "")
    result: dict[str, Any] = {
        "result": "BLOCKED",
        "branch": args.branch,
        "workflow": ALLOWED[args.branch],
        "errors": [],
    }
    try:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        sha = trigger(args.branch, args.message)
        run = wait_for_run(
            repository=repository,
            token=token,
            sha=sha,
            workflow_name=ALLOWED[args.branch],
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
        archive = api_bytes(
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
        evidence["canonical_verifier_head_sha"] = sha
        result = evidence
    except (
        OSError,
        ValueError,
        TimeoutError,
        subprocess.CalledProcessError,
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
