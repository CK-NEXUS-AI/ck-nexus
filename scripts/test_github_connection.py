#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

from creator_app.github_integration import GitHubIntegration


def main() -> int:
    integration = GitHubIntegration(
        os.getenv("GITHUB_TOKEN", ""),
        repository=os.getenv("GITHUB_REPO", ""),
        api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com"),
    )
    result = integration.status().as_dict()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["configured"]:
        return 2
    if not result["connected"]:
        return 1
    if os.getenv("GITHUB_REPO", "").strip() and not result["repository_access"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
