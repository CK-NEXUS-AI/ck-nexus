#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any


def api_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-workflow-artifact-waiter",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wait for an exact-head workflow and require its production artifact"
    )
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "spinlnw10-art/ck-nexus")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    encoded_sha = urllib.parse.quote(args.head_sha, safe="")
    runs_url = (
        f"https://api.github.com/repos/{repository}/actions/runs"
        f"?head_sha={encoded_sha}&per_page=100"
    )
    deadline = time.monotonic() + args.timeout_seconds
    selected: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        runs = api_json(runs_url, token).get("workflow_runs", [])
        matches = [run for run in runs if run.get("name") == args.workflow_name]
        if matches:
            selected = sorted(matches, key=lambda item: int(item.get("id", 0)), reverse=True)[0]
            if selected.get("status") == "completed":
                break
        time.sleep(10)
    if selected is None or selected.get("status") != "completed":
        raise SystemExit(f"timed out waiting for workflow {args.workflow_name!r}")
    if selected.get("conclusion") != "success":
        raise SystemExit(
            f"workflow {args.workflow_name!r} concluded {selected.get('conclusion')!r}"
        )

    run_id = int(selected["id"])
    artifacts_url = (
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"
    )
    artifacts = api_json(artifacts_url, token).get("artifacts", [])
    matching = [
        artifact
        for artifact in artifacts
        if str(artifact.get("name", "")).startswith(args.artifact_prefix)
        and artifact.get("expired") is False
    ]
    if not matching:
        raise SystemExit(
            f"workflow succeeded but no non-expired artifact starts with {args.artifact_prefix!r}"
        )
    print(
        json.dumps(
            {
                "result": "PASS",
                "workflow_name": args.workflow_name,
                "run_id": run_id,
                "head_sha": args.head_sha,
                "artifacts": [
                    {
                        "id": int(artifact["id"]),
                        "name": artifact.get("name"),
                        "digest": artifact.get("digest"),
                    }
                    for artifact in matching
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
