#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


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
            "User-Agent": "ck-nexus-workflow-dispatcher",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status == 204:
            return {}
        return json.load(response)


def runs(
    *, repository: str, token: str, workflow_file: str, branch: str
) -> list[dict[str, Any]]:
    encoded_branch = urllib.parse.quote(branch, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"{workflow_file}/runs?branch={encoded_branch}&event=workflow_dispatch&per_page=100"
    )
    return list(request_json(url, token).get("workflow_runs", []))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dispatch an exact-ref workflow and require a real non-expired artifact"
    )
    parser.add_argument("--workflow-file", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--expected-head-sha")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "spinlnw10-art/ck-nexus")
    token = os.environ.get("GITHUB_TOKEN", "")
    result: dict[str, Any] = {"result": "BLOCKED", "errors": []}
    try:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        before = runs(
            repository=repository,
            token=token,
            workflow_file=args.workflow_file,
            branch=args.ref,
        )
        previous_ids = {int(item["id"]) for item in before}
        dispatch_url = (
            f"https://api.github.com/repos/{repository}/actions/workflows/"
            f"{args.workflow_file}/dispatches"
        )
        request_json(
            dispatch_url,
            token,
            method="POST",
            payload={"ref": args.ref},
        )

        deadline = time.monotonic() + args.timeout_seconds
        selected: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            candidates = [
                item
                for item in runs(
                    repository=repository,
                    token=token,
                    workflow_file=args.workflow_file,
                    branch=args.ref,
                )
                if int(item.get("id", 0)) not in previous_ids
                and item.get("name") == args.workflow_name
            ]
            if candidates:
                selected = sorted(
                    candidates,
                    key=lambda item: int(item.get("id", 0)),
                    reverse=True,
                )[0]
                if selected.get("status") == "completed":
                    break
            time.sleep(10)
        if selected is None or selected.get("status") != "completed":
            raise TimeoutError("dispatched workflow did not complete before timeout")
        if selected.get("conclusion") != "success":
            raise ValueError(
                f"workflow concluded {selected.get('conclusion')!r}"
            )
        if args.expected_head_sha and selected.get("head_sha") != args.expected_head_sha:
            raise ValueError(
                "workflow head SHA does not match the promoted closure evidence commit"
            )

        run_id = int(selected["id"])
        artifacts_url = (
            f"https://api.github.com/repos/{repository}/actions/runs/"
            f"{run_id}/artifacts?per_page=100"
        )
        artifacts = [
            artifact
            for artifact in request_json(artifacts_url, token).get("artifacts", [])
            if str(artifact.get("name", "")).startswith(args.artifact_prefix)
            and artifact.get("expired") is False
        ]
        if not artifacts:
            raise ValueError(
                "workflow completed but did not produce the required production artifact"
            )
        normalized = []
        for artifact in artifacts:
            digest = artifact.get("digest")
            if not isinstance(digest, str) or not digest.startswith("sha256:"):
                raise ValueError("production artifact is missing a server-side SHA-256 digest")
            normalized.append(
                {
                    "id": int(artifact["id"]),
                    "name": artifact.get("name"),
                    "digest": digest,
                }
            )
        result = {
            "result": "PASS",
            "workflow": args.workflow_name,
            "workflow_run_id": run_id,
            "head_sha": selected.get("head_sha"),
            "ref": args.ref,
            "artifacts": normalized,
            "production_ready_claim": False,
            "requires_human_release_review": True,
        }
    except (
        OSError,
        ValueError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
