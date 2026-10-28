#!/usr/bin/env python3
"""Publish verified CK-NEXUS branches and open draft PRs when configured."""

from __future__ import annotations

import json
import os
from pathlib import Path

from creator_app.n8n_intelligence.auto_gitops import AutoGitOps
from creator_app.n8n_intelligence.gitops_controller import SafeGitOpsController


def _write_evidence(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def _open_pending_pull_requests(evidence_dir: Path) -> list[dict[str, object]]:
    token = os.getenv("GITHUB_TOKEN", "")
    repo_name = os.getenv("GITHUB_REPO", "")
    if not token or not repo_name:
        return [{"state": "not_configured", "reason": "github_token_or_repo_missing"}]

    controller = SafeGitOpsController(
        token, repo_name, base=os.getenv("GITHUB_BASE_BRANCH", "main")
    )
    outcomes: list[dict[str, object]] = []
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("state") != "verified" or data.get("gitops_state") != "published":
            continue
        if data.get("pull_request_state") in {"created", "existing"}:
            continue
        try:
            result = controller.create_pull_request(
                task_id=str(data.get("job_id") or ""),
                branch=str(data.get("branch") or ""),
                commit_sha=str(data.get("commit_sha") or ""),
                state=str(data.get("state") or ""),
                tests_ok=data.get("tests_ok") is True,
                changed_paths=[str(item) for item in data.get("changed_paths", [])]
                if isinstance(data.get("changed_paths"), list)
                else [],
                reason=str(data.get("gitops_reason") or "Verified automated change"),
                error_reason=str(data.get("error_reason") or data.get("error_text") or "") or None,
            )
            data["pull_request_state"] = result.state
            data["pull_request_reason"] = result.reason
            if result.url:
                data["pull_request_url"] = result.url
            if result.number is not None:
                data["pull_request_number"] = result.number
            _write_evidence(path, data)
            outcomes.append(
                {
                    "job_id": data.get("job_id"),
                    "state": result.state,
                    "reason": result.reason,
                    "url": result.url,
                    "number": result.number,
                }
            )
        except Exception as exc:
            # Controller exceptions contain only sanitized status codes/reasons.
            outcomes.append(
                {
                    "job_id": data.get("job_id"),
                    "state": "blocked",
                    "reason": str(exc)
                    if str(exc).startswith("github_")
                    else "pull_request_creation_failed",
                }
            )
    return outcomes


def main() -> int:
    evidence_dir = Path(
        os.getenv("CKNEXUS_AUTO_DEV_EVIDENCE", "/var/lib/cknexus/n8n-intelligence/auto-dev")
    )
    repo = Path(os.getenv("CKNEXUS_REPO", "/root/ck-nexus"))
    remote = os.getenv("CKNEXUS_GITOPS_REMOTE", "origin")
    try:
        result = AutoGitOps(evidence_dir, repo_root=repo, remote=remote).run_once()
        pull_requests = _open_pending_pull_requests(evidence_dir)
        print(
            json.dumps(
                {
                    "ok": result.state in {"idle", "published", "skipped"},
                    "state": result.state,
                    "reason": result.reason,
                    "job_id": result.job_id,
                    "commit_sha": result.commit_sha,
                    "pull_requests": pull_requests,
                },
                sort_keys=True,
            )
        )
        return 0 if result.state in {"idle", "published", "skipped"} else 1
    except Exception:
        print(
            json.dumps({"ok": False, "error": "auto_gitops_initialization_failed"}, sort_keys=True)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
