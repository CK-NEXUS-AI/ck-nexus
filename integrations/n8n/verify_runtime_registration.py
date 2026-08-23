from __future__ import annotations

import argparse
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExpectedWebhook:
    workflow_name: str
    node_name: str
    path: str
    method: str
    webhook_id: str


class RegistrationError(RuntimeError):
    pass


def load_expected(paths: Iterable[Path]) -> list[ExpectedWebhook]:
    expected: list[ExpectedWebhook] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for node in data.get("nodes", []):
            if node.get("type") != "n8n-nodes-base.webhook":
                continue
            params = node.get("parameters", {})
            webhook_id = str(node.get("webhookId") or "").strip()
            webhook_path = str(params.get("path") or "").strip().strip("/")
            method = str(params.get("httpMethod") or "GET").upper()
            if not webhook_id:
                raise RegistrationError(f"missing webhookId: {path.name}:{node.get('name')}")
            if not webhook_path:
                raise RegistrationError(f"missing webhook path: {path.name}:{node.get('name')}")
            expected.append(
                ExpectedWebhook(
                    workflow_name=str(data.get("name") or path.stem),
                    node_name=str(node.get("name") or node.get("id") or "webhook"),
                    path=webhook_path,
                    method=method,
                    webhook_id=webhook_id,
                )
            )
    return expected


def read_rows(db_path: Path) -> list[tuple[str, str, str, str, str | None]]:
    con = sqlite3.connect(db_path)
    try:
        return list(
            con.execute(
                "select workflowId, webhookPath, method, node, webhookId from webhook_entity"
            )
        )
    finally:
        con.close()


def verify(db_path: Path, workflow_paths: list[Path]) -> dict[str, object]:
    expected = load_expected(workflow_paths)
    rows = read_rows(db_path)
    missing: list[str] = []
    stale: list[str] = []

    expected_pairs = {(item.path, item.method) for item in expected}
    for item in expected:
        if not any(path == item.path and method == item.method for _, path, method, _, _ in rows):
            missing.append(f"{item.method} {item.path}")

    for workflow_id, path, method, node, _ in rows:
        for expected_path, expected_method in expected_pairs:
            if method != expected_method:
                continue
            if path == expected_path:
                continue
            if path.endswith("/" + expected_path):
                stale.append(f"{workflow_id}:{node}:{method}:{path}")

    result = {
        "ok": not missing and not stale,
        "expected": [f"{item.method} {item.path}" for item in expected],
        "missing": sorted(set(missing)),
        "stale": sorted(set(stale)),
        "row_count": len(rows),
    }
    if not result["ok"]:
        raise RegistrationError(json.dumps(result, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("workflows", nargs="+", type=Path)
    args = parser.parse_args()
    result = verify(args.db, args.workflows)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
