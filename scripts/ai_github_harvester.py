from __future__ import annotations

import http.client
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "ai_factory" / "github_signals.jsonl"


def classify_cli_error(stderr: str) -> str:
    """Return a safe error category without exposing raw CLI output or credentials."""
    message = stderr.lower()
    if "api rate limit exceeded" in message or "rate limit" in message or "http 429" in message:
        return "rate_limited"
    if (
        "bad credentials" in message
        or "http 401" in message
        or "authentication required" in message
    ):
        return "authentication_failed"
    if "http 422" in message or "validation failed" in message or "invalid query" in message:
        return "invalid_query"
    if "resource not accessible by integration" in message or "http 403" in message:
        return "permission_denied"
    if "could not resolve host" in message or "name or service not known" in message:
        return "network_dns_error"
    if "timed out" in message or "timeout" in message:
        return "network_timeout"
    return "unclassified_cli_error"


def _github_token() -> str:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    result = subprocess.run(
        ["gh", "auth", "token"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        shell=False,
        close_fds=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("github_authentication_unavailable")
    return result.stdout.strip()


def search(query: str, limit: int = 20) -> list[dict]:
    """Search GitHub via a fixed API origin; user query is URL-encoded data."""
    query = query.strip()
    if not query or len(query) > 240 or not re.fullmatch(r"[A-Za-z0-9_:/.*><=+\- ]+", query):
        raise ValueError("GitHub search query contains unsupported characters")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("GitHub search limit must be between 1 and 100")
    connection = http.client.HTTPSConnection("api.github.com", timeout=20)
    try:
        connection.request(
            "GET",
            "/search/repositories?" + urlencode({"q": query, "per_page": limit}),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + _github_token(),
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: GitHub search failed")
        payload = json.loads(response.read(2_000_000))
    except Exception as exc:
        category = classify_cli_error(str(exc))
        raise RuntimeError(f"github_search_failed:{category}") from None
    finally:
        connection.close()
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
    print(
        json.dumps(
            {
                "kind": "GITHUB_MARKET_HARVEST",
                "queries": len(queries),
                "output": str(OUT),
                "provenance": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
