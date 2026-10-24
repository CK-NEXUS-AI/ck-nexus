#!/usr/bin/env python3
"""Publish verified CK-NEXUS Auto Developer branches to GitHub."""

from __future__ import annotations

import json
import os
from pathlib import Path

from creator_app.n8n_intelligence.auto_gitops import AutoGitOps


def main() -> int:
    evidence_dir = Path(
        os.getenv("CKNEXUS_AUTO_DEV_EVIDENCE", "/var/lib/cknexus/n8n-intelligence/auto-dev")
    )
    repo = Path(os.getenv("CKNEXUS_REPO", "/root/ck-nexus"))
    remote = os.getenv("CKNEXUS_GITOPS_REMOTE", "origin")
    try:
        result = AutoGitOps(evidence_dir, repo_root=repo, remote=remote).run_once()
        print(
            json.dumps(
                {
                    "ok": result.state in {"idle", "published", "skipped"},
                    "state": result.state,
                    "reason": result.reason,
                    "job_id": result.job_id,
                    "commit_sha": result.commit_sha,
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
