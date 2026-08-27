#!/usr/bin/env python3
"""Online exact-head GitHub evidence checker for the Master Capability Registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from scripts.validate_master_capability_evidence_registry import SHA1_RE, load_registry

RUN_ID_RE = re.compile(r"(?<!\d)(\d{8,})(?!\d)")


def validate_exact_head_runs(
    data: dict[str, Any],
    runs_for_sha: Callable[[str], list[dict[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    for record in data.get("records", []):
        if record.get("maturity") != "M3_MEASURED" or record.get("source") != "DEV_PR":
            continue
        rid = str(record.get("id", "<missing>"))
        sha = str(record.get("sha", ""))
        if not SHA1_RE.fullmatch(sha):
            errors.append(f"{rid}: M3 DEV_PR lacks exact subject sha")
            continue

        runs = runs_for_sha(sha)
        successful = [
            run
            for run in runs
            if run.get("head_sha") == sha and run.get("conclusion") == "success"
        ]
        if not successful:
            errors.append(f"{rid}: no successful GitHub Actions run bound to exact subject {sha}")
            continue

        exact_ids = {int(run["id"]) for run in successful if run.get("id") is not None}
        for evidence in record.get("evidence", []):
            if evidence.get("kind") != "GITHUB_ACTIONS" or evidence.get("status") != "SUCCESS":
                continue
            ids = {int(match) for match in RUN_ID_RE.findall(str(evidence.get("ref", "")))}
            if ids and not ids.issubset(exact_ids):
                missing = sorted(ids - exact_ids)
                errors.append(
                    f"{rid}: listed successful run id(s) not bound to exact subject {sha}: {missing}"
                )
    return errors


def _github_runs_fetcher(repo: str, token: str) -> Callable[[str], list[dict[str, Any]]]:
    cache: dict[str, list[dict[str, Any]]] = {}

    def fetch(sha: str) -> list[dict[str, Any]]:
        if sha in cache:
            return cache[sha]
        query = urllib.parse.urlencode({"head_sha": sha, "per_page": 100})
        url = f"https://api.github.com/repos/{repo}/actions/runs?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ck-nexus-master-registry-verifier",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        runs = payload.get("workflow_runs", [])
        if not isinstance(runs, list):
            raise RuntimeError("GitHub Actions response missing workflow_runs list")
        cache[sha] = runs
        return runs

    return fetch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index",
        nargs="?",
        type=Path,
        default=Path("config/master_capability_evidence_registry.v1.json"),
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN is required for exact-head evidence verification")
        return 1

    data = load_registry(args.index)
    repo = str(data.get("baseline", {}).get("repo", ""))
    if not repo or "/" not in repo:
        print("ERROR: registry baseline repo is invalid")
        return 1

    try:
        errors = validate_exact_head_runs(data, _github_runs_fetcher(repo, token))
    except Exception as exc:  # network/API errors must fail closed
        print(f"ERROR: exact-head GitHub evidence lookup failed: {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Exact-head GitHub measurement bindings: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
