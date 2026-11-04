from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

REPO = "spinlnw10-art/ck-nexus"
FROZEN_SOURCE = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
FROZEN_TREE = "0525195934f703a8becf8a39f6397b2411e0bb2e"
RUNTIME_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
APPLICATION_SUBJECT = "dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec"

TEXT_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql",
    ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".sh", ".ps1", ".xml",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count(path: Path) -> int | None:
    if path.suffix.lower() not in TEXT_EXTS and path.name not in {"Dockerfile", "LICENSE"}:
        return None
    try:
        with path.open("r", encoding="utf-8", errors="strict") as f:
            return sum(1 for _ in f)
    except (UnicodeDecodeError, OSError):
        return None


def main() -> int:
    out = Path("commercial-readiness-evidence")
    out.mkdir(exist_ok=True)

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    tracked = [p for p in git("ls-files", "-z").split("\0") if p]

    rows: list[dict[str, object]] = []
    loc = Counter()
    total_size = 0

    for rel in tracked:
        path = Path(rel)
        if not path.is_file():
            continue
        size = path.stat().st_size
        total_size += size
        lines = line_count(path)
        ext = path.suffix.lower() or path.name
        if lines is not None:
            loc[ext] += lines
        rows.append(
            {
                "path": rel,
                "size_bytes": size,
                "sha256": sha256_file(path),
                "type": ext,
                "loc": "" if lines is None else lines,
            }
        )

    rows.sort(key=lambda r: str(r["path"]))

    with (out / "inventory.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "size_bytes", "sha256", "type", "loc"])
        writer.writeheader()
        writer.writerows(rows)

    with (out / "manifest.sha256").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(f'{row["sha256"]}  {row["path"]}\n')

    readiness = {
        "schema_version": 1,
        "repository": REPO,
        "head_sha": head,
        "tree_sha": tree,
        "tracked_file_count": len(rows),
        "total_size_bytes": total_size,
        "loc_by_type": dict(sorted(loc.items())),
        "production_authority": {
            "frozen_source_sha": FROZEN_SOURCE,
            "frozen_tree_sha": FROZEN_TREE,
            "runtime_subject_sha256": RUNTIME_SUBJECT,
            "application_subject_sha256": APPLICATION_SUBJECT,
            "q10": "NOT_VERIFIED",
            "q11": "BLOCKED",
            "q12": "BLOCKED",
            "production_ready": False,
            "commercial_ready": False,
            "pr14_merge_authorized": False,
        },
        "classification": "POST_P0_DEVELOPMENT_EVIDENCE_ONLY",
        "note": "This artifact cannot promote Q10/Q11/Q12 and cannot authorize production merge/deploy.",
    }

    (out / "readiness.json").write_text(
        json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = [
        "# Commercial Readiness Evidence Summary",
        "",
        f"- repository: `{REPO}`",
        f"- head: `{head}`",
        f"- tree: `{tree}`",
        f"- tracked files: **{len(rows)}**",
        f"- total bytes: **{total_size}**",
        "- classification: **POST_P0_DEVELOPMENT_EVIDENCE_ONLY**",
        "- Q10: **NOT_VERIFIED**",
        "- Q11: **BLOCKED**",
        "- Q12: **BLOCKED**",
        "- Production: **NO-GO**",
        "",
        "## LOC by type",
        "",
    ]
    summary.extend(f"- `{k}`: {v}" for k, v in sorted(loc.items()))
    summary.extend(
        [
            "",
            "This report is inventory/evidence metadata only and must not be used to bypass canonical production gates.",
        ]
    )
    (out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
