#!/usr/bin/env python3
"""Read-only repository file retention audit for CK-NEXUS."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import zipfile
from collections import Counter, defaultdict
from pathlib import PurePosixPath

ROOT_KEEP = {
    ".gitignore", ".env.example", "Dockerfile", "docker-compose.prod.yml",
    "main.py", "pyproject.toml", "uv.lock", "README.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "RELEASE_STATUS.md", "SHA256SUMS",
}
CORE_PREFIXES = (
    "creator_app/", "services/", "gateway/", "orchestration/", "idea_engine/",
    "migrations/", "tests/", ".github/workflows/", ".github/release-tools/",
    "deploy/", "observability/",
)
ARCHIVE_HINTS = (
    "backup", "snapshot", "recovery", "historical", "legacy", "old", "archive",
    "validation_report", "changelog", "demo", "notes",
)
DELETE_HINTS = (
    "__pycache__/", ".pytest_cache/", ".ruff_cache/", ".mypy_cache/",
    ".coverage", ".DS_Store", ".pyc", ".pyo", ".swp", "~",
)
SENSITIVE_NAME_HINTS = (
    ".env", "id_rsa", "id_ed25519", "private_key", "credentials",
    "token", "secret", "password",
)
TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".sh", ".ps1", ".js", ".ts", ".tsx", ".css", ".html", ".sql", ".csv",
    ".xml", ".graphql", ".dockerfile",
}


def run(*args: str, check: bool = True) -> str:
    proc = subprocess.run(args, check=check, text=True, capture_output=True)
    return proc.stdout


def git_bytes(ref: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        check=True,
        capture_output=True,
    )
    return proc.stdout


def git_blob_bytes(blob_sha: str) -> bytes:
    proc = subprocess.run(
        ["git", "cat-file", "-p", blob_sha],
        check=True,
        capture_output=True,
    )
    return proc.stdout


def list_tree(ref: str) -> list[tuple[str, str, str, int]]:
    raw = run("git", "ls-tree", "-rl", "-z", ref)
    rows = []
    for item in raw.split("\0"):
        if not item:
            continue
        meta, path = item.split("\t", 1)
        mode, kind, sha, size = meta.split(" ", 3)
        if kind != "blob":
            continue
        rows.append((path, sha, mode, int(size) if size.isdigit() else 0))
    return rows


def is_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    sample = data[:8192]
    if not sample:
        return False
    bad = sum(byte < 9 or (13 < byte < 32) for byte in sample)
    return bad / len(sample) > 0.15


def category(path: str) -> str:
    p = path.lower()
    if path in ROOT_KEEP:
        return "ROOT_CANONICAL"
    if p.startswith(".github/workflows/"):
        return "GITHUB_WORKFLOW"
    if p.startswith(".github/"):
        return "GITHUB_GOVERNANCE"
    if p.startswith("tests/") or "/tests/" in p or PurePosixPath(path).name.startswith("test_"):
        return "TEST"
    if p.startswith("evidence/"):
        return "EVIDENCE"
    if p.startswith("docs/") or p.endswith(".md"):
        return "DOCUMENTATION"
    if p.startswith("migrations/") or p.endswith(".sql"):
        return "MIGRATION"
    if p.startswith("scripts/") or p.startswith("runbooks/"):
        return "OPERATIONS_SCRIPT"
    if p.startswith(("creator_app/", "services/", "gateway/", "orchestration/", "idea_engine/")):
        return "CORE_SOURCE"
    if p.startswith(("deploy/", "observability/")):
        return "INFRASTRUCTURE"
    if p.endswith((".json", ".yml", ".yaml", ".toml", ".ini", ".cfg")):
        return "CONFIG_DATA"
    if p.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".tar", ".gz")):
        return "BINARY_ASSET"
    return "OTHER"


def structural_signals(path: str, text: str) -> dict[str, object]:
    ext = PurePosixPath(path).suffix.lower()
    sig: dict[str, object] = {}
    if ext == ".py":
        sig["functions"] = len(re.findall(r"(?m)^\s*(?:async\s+)?def\s+\w+", text))
        sig["classes"] = len(re.findall(r"(?m)^\s*class\s+\w+", text))
        sig["imports"] = len(re.findall(r"(?m)^\s*(?:from\s+\S+\s+import|import\s+)", text))
        sig["main_guard"] = "__name__" in text and "__main__" in text
    elif ext in {".yml", ".yaml"}:
        sig["uses_actions"] = re.findall(r"uses:\s*([^\s#]+)", text)
        sig["mutable_action_refs"] = [
            value for value in sig["uses_actions"]
            if "@" in value and not re.search(r"@[0-9a-fA-F]{40}$", value)
        ]
        sig["secret_refs"] = sorted(set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)))
        sig["has_permissions"] = bool(re.search(r"(?m)^permissions:\s*$", text))
        sig["workflow_dispatch"] = "workflow_dispatch" in text
        sig["pull_request"] = bool(re.search(r"(?m)^\s*pull_request:", text))
        sig["push"] = bool(re.search(r"(?m)^\s*push:", text))
    elif ext == ".json":
        try:
            obj = json.loads(text)
            sig["json_valid"] = True
            if isinstance(obj, dict):
                sig["top_keys"] = sorted(obj)[:30]
                for key in ("schema_version", "status", "result", "gate", "production_status"):
                    if key in obj:
                        sig[key] = obj[key]
        except Exception:
            sig["json_valid"] = False
    elif ext == ".md":
        sig["headings"] = len(re.findall(r"(?m)^#{1,6}\s+", text))
        sig["status_terms"] = sorted(set(re.findall(
            r"\b(?:PASS|FAIL|BLOCKED|NO-GO|NOT_VERIFIED|VERIFIED|SUPERSEDED)\b",
            text,
        )))
    elif ext == ".sh" or path.endswith(".bash"):
        sig["strict_mode"] = "set -euo pipefail" in text
        sig["shebang"] = text.startswith("#!")
    return sig


SECRET_CONTENT_PATTERNS = {
    "openai_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "github_token": re.compile(rb"(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}"),
    "private_key": re.compile(rb"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
}


def archive_signals(path: str, data: bytes) -> dict[str, object]:
    low = path.lower()
    names: list[str] = []
    content_hits: set[str] = set()

    def inspect_member(name: str, payload: bytes | None) -> None:
        names.append(name)
        if payload is None or len(payload) > 2_000_000:
            return
        for label, pattern in SECRET_CONTENT_PATTERNS.items():
            if pattern.search(payload):
                content_hits.add(label)

    try:
        if low.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    payload = None
                    if not info.is_dir() and info.file_size <= 2_000_000:
                        payload = archive.read(info)
                    inspect_member(info.filename, payload)
        elif low.endswith(".tar.gz.b64"):
            decoded = base64.b64decode(b"".join(data.split()), validate=True)
            with tarfile.open(fileobj=io.BytesIO(decoded), mode="r:gz") as archive:
                for member in archive.getmembers():
                    payload = None
                    if member.isfile() and member.size <= 2_000_000:
                        handle = archive.extractfile(member)
                        payload = handle.read() if handle is not None else None
                    inspect_member(member.name, payload)
        else:
            return {}
    except Exception as exc:
        return {"archive_parse_error": type(exc).__name__}

    sensitive_names = sorted(
        name
        for name in names
        if any(hint.lower() in name.lower() for hint in SENSITIVE_NAME_HINTS)
    )
    return {
        "archive_member_count": len(names),
        "archive_member_sample": sorted(names)[:100],
        "sensitive_member_names": sensitive_names[:100],
        "secret_pattern_categories_found": sorted(content_hits),
    }


def retention(path: str, cat: str, size: int, binary: bool, text: str) -> tuple[str, list[str]]:
    low = path.lower()
    reasons: list[str] = []
    if any(hint in low for hint in DELETE_HINTS):
        return "DELETE_CANDIDATE", ["generated/cache/editor artifact pattern"]
    if any(PurePosixPath(path).name.lower() == hint for hint in SENSITIVE_NAME_HINTS):
        return "REVIEW", ["sensitive filename"]
    if any(hint in PurePosixPath(path).name.lower() for hint in SENSITIVE_NAME_HINTS):
        reasons.append("sensitive-looking filename; verify no secret material")
    if path in ROOT_KEEP or path.startswith(CORE_PREFIXES):
        reasons.append("canonical runtime/test/workflow path")
        return "KEEP", reasons
    if cat in {"MIGRATION", "INFRASTRUCTURE", "GITHUB_GOVERNANCE"}:
        return "KEEP", ["operational/governance dependency"]
    if cat == "EVIDENCE":
        return "KEEP_RETAIN_HISTORY", ["evidence/provenance should not be silently deleted"]
    if cat == "DOCUMENTATION":
        if any(hint in low for hint in ARCHIVE_HINTS):
            return "ARCHIVE_CANDIDATE", ["historical/validation/demo documentation"]
        return "KEEP", ["active project documentation"]
    if cat == "BINARY_ASSET":
        reasons.append("binary asset requires provenance/manual usefulness review")
        if size > 2_000_000:
            reasons.append("large tracked binary")
        return "REVIEW", reasons
    if size == 0:
        return "REVIEW", ["empty tracked file"]
    if binary:
        return "REVIEW", ["binary/opaque tracked content"]
    return "REVIEW", reasons or ["no automatic deletion basis"]


def reachable_blob_inventory(main_blob_shas: set[str]) -> list[dict[str, object]]:
    rev_list = run("git", "rev-list", "--objects", "--all", check=False)
    if not rev_list.strip():
        return []

    proc = subprocess.run(
        [
            "git",
            "cat-file",
            "--batch-check=%(objectname)%09%(objecttype)%09%(objectsize)%09%(rest)",
        ],
        input=rev_list,
        text=True,
        capture_output=True,
        check=False,
    )
    rows: dict[str, dict[str, object]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 3:
            continue
        sha, kind, raw_size = parts[:3]
        path = parts[3] if len(parts) == 4 else ""
        if kind != "blob":
            continue
        item = rows.setdefault(
            sha,
            {
                "blob_sha": sha,
                "size_bytes": int(raw_size),
                "paths": set(),
                "on_main": sha in main_blob_shas,
            },
        )
        if path:
            item["paths"].add(path)

    results = []
    for sha, item in rows.items():
        if item["on_main"]:
            continue
        paths = sorted(item["paths"])
        representative = paths[0] if paths else f"<historical-blob:{sha}>"
        data = git_blob_bytes(sha)
        binary = is_binary(data)
        text = "" if binary else data.decode("utf-8", errors="replace")
        cat = category(representative)
        decision, reasons = retention(
            representative,
            cat,
            len(data),
            binary,
            text,
        )
        signals = structural_signals(representative, text) if text else {}
        archive = archive_signals(representative, data)
        if archive:
            signals["archive"] = archive
        secret_categories = sorted(
            label
            for label, pattern in SECRET_CONTENT_PATTERNS.items()
            if pattern.search(data)
        )
        results.append(
            {
                "blob_sha": sha,
                "sha256": hashlib.sha256(data).hexdigest(),
                "representative_path": representative,
                "paths": paths[:100],
                "path_count": len(paths),
                "size_bytes": len(data),
                "binary": binary,
                "line_count": 0 if binary else len(text.splitlines()),
                "category": cat,
                "retention": decision,
                "reasons": reasons,
                "signals": signals,
                "secret_pattern_categories_found": secret_categories,
            }
        )
    return results


def last_change(ref: str, path: str) -> dict[str, str]:
    out = run(
        "git", "log", "-1", "--format=%H%x09%cI%x09%s", ref, "--", path,
        check=False,
    ).strip()
    if not out:
        return {}
    parts = out.split("\t", 2)
    if len(parts) != 3:
        return {}
    return {"commit": parts[0], "date": parts[1], "subject": parts[2]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--out-dir", default="repo-audit")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    rows = []
    text_cache: dict[str, str] = {}
    digest_paths: dict[str, list[str]] = defaultdict(list)

    for path, blob_sha, mode, tree_size in list_tree(args.ref):
        data = git_bytes(args.ref, path)
        digest = hashlib.sha256(data).hexdigest()
        digest_paths[digest].append(path)
        binary = is_binary(data)
        text = ""
        if not binary:
            text = data.decode("utf-8", errors="replace")
            text_cache[path] = text
        cat = category(path)
        decision, reasons = retention(path, cat, len(data), binary, text)
        signals = structural_signals(path, text) if text else {}
        change = last_change(args.ref, path)
        rows.append({
            "path": path,
            "blob_sha": blob_sha,
            "sha256": digest,
            "mode": mode,
            "size_bytes": len(data),
            "tree_size": tree_size,
            "binary": binary,
            "line_count": 0 if binary else len(text.splitlines()),
            "category": cat,
            "retention": decision,
            "reasons": reasons,
            "signals": signals,
            "last_change": change,
        })

    path_mentions = Counter()
    text_items = list(text_cache.items())
    for target in rows:
        path = target["path"]
        base = PurePosixPath(path).name
        if len(base) < 5:
            continue
        mentions = 0
        for other_path, text in text_items:
            if other_path == path:
                continue
            if path in text or base in text:
                mentions += 1
        path_mentions[path] = mentions
        target["reference_mentions"] = mentions

    duplicate_groups = [
        {"sha256": digest, "paths": paths}
        for digest, paths in digest_paths.items()
        if len(paths) > 1
    ]

    branch_rows = []
    branch_blob_context: dict[str, dict[str, object]] = {}
    run("git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", check=False)
    main_paths = {row["path"] for row in rows}
    main_blob_shas = {row["blob_sha"] for row in rows}
    refs = run(
        "git",
        "for-each-ref",
        "--format=%(refname:short)%09%(objectname)%09%(committerdate:iso-strict)",
        "refs/remotes/origin/",
    ).splitlines()
    for line in refs:
        if not line or line.startswith("origin/HEAD"):
            continue
        branch, sha, date = line.split("\t", 2)
        try:
            tree_items = list_tree(branch)
        except Exception:
            continue
        paths = {item[0] for item in tree_items}
        for path, blob_sha, mode, size in tree_items:
            context = branch_blob_context.setdefault(
                blob_sha,
                {
                    "paths": set(),
                    "branches": set(),
                    "size_bytes": size,
                    "mode": mode,
                },
            )
            context["paths"].add(path)
            context["branches"].add(branch)
        branch_rows.append(
            {
                "branch": branch,
                "sha": sha,
                "date": date,
                "file_count": len(paths),
                "unique_vs_main_count": len(paths - main_paths),
                "missing_vs_main_count": len(main_paths - paths),
                "unique_vs_main_sample": sorted(paths - main_paths)[:50],
            }
        )

    historical_blobs = []
    for blob_sha, context in branch_blob_context.items():
        if blob_sha in main_blob_shas:
            continue
        paths = sorted(context["paths"])
        branches = sorted(context["branches"])
        representative = paths[0]
        data = git_blob_bytes(blob_sha)
        binary = is_binary(data)
        text = "" if binary else data.decode("utf-8", errors="replace")
        cat = category(representative)
        decision, reasons = retention(
            representative,
            cat,
            len(data),
            binary,
            text,
        )
        signals = structural_signals(representative, text) if text else {}
        archive = archive_signals(representative, data)
        if archive:
            signals["archive"] = archive
        historical_blobs.append(
            {
                "blob_sha": blob_sha,
                "sha256": hashlib.sha256(data).hexdigest(),
                "representative_path": representative,
                "paths": paths[:100],
                "path_count": len(paths),
                "branches": branches[:100],
                "branch_count": len(branches),
                "size_bytes": len(data),
                "binary": binary,
                "line_count": 0 if binary else len(text.splitlines()),
                "category": cat,
                "retention": decision,
                "reasons": reasons,
                "signals": signals,
            }
        )

    historical_reachable_blobs = reachable_blob_inventory(main_blob_shas)

    summary = {
        "ref": args.ref,
        "commit": run("git", "rev-parse", args.ref).strip(),
        "tree": run("git", "rev-parse", f"{args.ref}^{{tree}}").strip(),
        "file_count": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "categories": dict(Counter(row["category"] for row in rows)),
        "retention": dict(Counter(row["retention"] for row in rows)),
        "duplicate_groups": len(duplicate_groups),
        "branch_count_seen": len(branch_rows),
        "branch_only_unique_blobs": len(historical_blobs),
        "branch_only_retention": dict(
            Counter(item["retention"] for item in historical_blobs)
        ),
        "reachable_history_unique_blobs": len(historical_reachable_blobs),
        "reachable_history_retention": dict(
            Counter(item["retention"] for item in historical_reachable_blobs)
        ),
        "reachable_history_secret_signal_blobs": sum(
            bool(item["secret_pattern_categories_found"])
            for item in historical_reachable_blobs
        ),
        "large_files_over_1mb": [
            {"path": row["path"], "size_bytes": row["size_bytes"]}
            for row in rows if int(row["size_bytes"]) > 1_000_000
        ],
        "delete_candidates": [
            {"path": row["path"], "reasons": row["reasons"]}
            for row in rows if row["retention"] == "DELETE_CANDIDATE"
        ],
        "archive_candidates": [
            {"path": row["path"], "reasons": row["reasons"]}
            for row in rows if row["retention"] == "ARCHIVE_CANDIDATE"
        ],
        "review_candidates": [
            {"path": row["path"], "reasons": row["reasons"]}
            for row in rows if row["retention"] == "REVIEW"
        ],
    }

    with open(
        os.path.join(args.out_dir, "repo-file-audit.json"), "w", encoding="utf-8"
    ) as handle:
        payload = {
            "summary": summary,
            "files": rows,
            "duplicates": duplicate_groups,
            "branches": branch_rows,
            "branch_only_unique_blobs": historical_blobs,
            "reachable_history_unique_blobs": historical_reachable_blobs,
        }
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    with open(
        os.path.join(args.out_dir, "repo-file-audit.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "path",
                "category",
                "retention",
                "size_bytes",
                "lines",
                "binary",
                "reference_mentions",
                "sha256",
                "last_change_date",
                "reasons",
            ]
        )
        for row in rows:
            writer.writerow([
                row["path"], row["category"], row["retention"], row["size_bytes"],
                row["line_count"], row["binary"], row.get("reference_mentions", 0),
                row["sha256"], row["last_change"].get("date", ""),
                "; ".join(row["reasons"]),
            ])

    md = [
        "# CK-NEXUS Repository File Retention Audit",
        "",
        f"- Ref: `{summary['ref']}`",
        f"- Commit: `{summary['commit']}`",
        f"- Tree: `{summary['tree']}`",
        f"- Tracked files: **{summary['file_count']}**",
        f"- Total tracked bytes: **{summary['total_bytes']}**",
        f"- Duplicate content groups: **{summary['duplicate_groups']}**",
        f"- Remote branches inspected: **{summary['branch_count_seen']}**",
        f"- Branch-only unique file blobs: **{summary['branch_only_unique_blobs']}**",
        (
            "- Reachable historical unique blobs outside main: "
            f"**{summary['reachable_history_unique_blobs']}**"
        ),
        (
            "- Historical blobs with secret-pattern category signals: "
            f"**{summary['reachable_history_secret_signal_blobs']}**"
        ),
        "",
        "## Retention counts",
        "",
    ]
    for key, value in sorted(summary["retention"].items()):
        md.append(f"- {key}: **{value}**")
    md.extend(["", "## Category counts", ""])
    for key, value in sorted(summary["categories"].items()):
        md.append(f"- {key}: **{value}**")
    for title, key in [
        ("Delete candidates — proposal only, nothing deleted", "delete_candidates"),
        ("Archive candidates", "archive_candidates"),
        ("Manual review candidates", "review_candidates"),
    ]:
        md.extend(["", f"## {title}", ""])
        items = summary[key]
        if not items:
            md.append("- None")
        else:
            for item in items[:200]:
                md.append(f"- `{item['path']}` — {', '.join(item['reasons'])}")
    md.extend([
        "",
        "## Safety boundary",
        "",
        "This audit is read-only. DELETE_CANDIDATE is only a classification signal.",
        "No file or branch is deleted by this script.",
    ])
    with open(os.path.join(args.out_dir, "repo-file-audit.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(md) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
