from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "ai_factory" / "github_signals.jsonl"


def search(query: str, limit: int = 20) -> list[dict]:
    command = [
        "gh", "api", "search/repositories",
        "-f", "q=" + query,
        "-f", "per_page=" + str(limit),
    ]
    result = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError("github_search_failed")
    payload = json.loads(result.stdout)
    return payload.get("items", [])


def main() -> int:
    queries = os.environ.get(
        "AI_FACTORY_GITHUB_QUERIES",
        "topic:ai-agents stars:>100,topic:mcp stars:>100,topic:developer-tools stars:>100",
    ).split(",")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(UTC).isoformat()

    with OUT.open("w", encoding="utf-8") as handle:
        for query in queries:
            for item in search(query.strip()):
                signal = {
                    "schema_version": 1,
                    "kind": "GITHUB_MARKET_SIGNAL",
                    "captured_at": captured_at,
                    "source": "github",
                    "query": query.strip(),
                    "repository": item.get("full_name"),
                    "url": item.get("html_url"),
                    "description": item.get("description"),
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "open_issues": item.get("open_issues_count", 0),
                    "language": item.get("language"),
                    "updated_at": item.get("updated_at"),
                    "license": (item.get("license") or {}).get("spdx_id"),
                }
                handle.write(json.dumps(signal, sort_keys=True) + "\n")
    print(json.dumps({
        "kind": "GITHUB_MARKET_HARVEST",
        "queries": len(queries),
        "output": str(OUT),
        "provenance": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
