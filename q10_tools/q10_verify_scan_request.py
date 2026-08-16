#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REQ = Path("evidence/q10/Q10_SCAN_REQUEST.json")
EXPECTED_SHA = "45fde79c717b09f8675645aa541a5834ebd4f433"
EXPECTED_TREE = "8bb93b75237ac9891a6c60854f705459dc263921"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> int:
    data = json.loads(REQ.read_text(encoding="utf-8"))
    assert data["gate"] == "Q10"
    assert data["status"] == "PREPARED_NOT_EXECUTED"
    assert data["required_executor"] == "Codex Security Deep Security Scan"
    assert data["target_sha"] == EXPECTED_SHA
    assert data["target_tree_sha"] == EXPECTED_TREE
    assert data["target_scope"] == "."
    assert data["scan_mode"] == "deep"
    assert data["production_status"] == "NO-GO"
    assert data["acceptance"]["must_use_native_codex_security_deep_scan"] is True
    assert "manual-review-only" in data["prohibited_substitutions"]

    git("cat-file", "-e", f"{EXPECTED_SHA}^{{commit}}")
    actual_tree = git("show", "-s", "--format=%T", EXPECTED_SHA)
    assert actual_tree == EXPECTED_TREE, (actual_tree, EXPECTED_TREE)

    print("Q10_PREPARED_NOT_EXECUTED")
    print(f"target_sha={EXPECTED_SHA}")
    print(f"target_tree={actual_tree}")
    print("production_status=NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
