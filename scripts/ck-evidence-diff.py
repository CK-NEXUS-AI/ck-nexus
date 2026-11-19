#!/usr/bin/env python3
"""Compare two CK-NEXUS evidence directories without modifying either source."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (ROOT / "evidence").resolve()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def files_map(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name == "SHA256SUMS":
            continue
        rel = p.relative_to(root).as_posix()
        result[rel] = sha256(p)
    return result


def verify_sums(root: Path) -> dict[str, object]:
    manifest = root / "SHA256SUMS"
    if not manifest.is_file():
        return {"status": "WARN", "checked": 0, "failed": [], "detail": "SHA256SUMS missing"}
    checked = 0
    failed: list[str] = []
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        if "  " not in line:
            failed.append(f"malformed-line:{checked + 1}")
            continue
        expected, rel = line.split("  ", 1)
        target = (root / rel).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            failed.append(f"invalid-or-missing-path:{rel}")
            continue
        checked += 1
        if sha256(target) != expected:
            failed.append(f"hash-mismatch:{rel}")
    return {
        "status": "PASS" if not failed else "FAIL",
        "checked": checked,
        "failed": failed,
        "detail": "checksums verified" if not failed else "checksum verification failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", help="first evidence directory")
    parser.add_argument("right", help="second evidence directory")
    parser.add_argument("--output-dir", help="output directory under repository evidence/")
    args = parser.parse_args()
    left = Path(args.left).expanduser().resolve()
    right = Path(args.right).expanduser().resolve()
    for label, path in (("left", left), ("right", right)):
        if not path.is_dir() or not path.is_relative_to(EVIDENCE_ROOT):
            print(
                f"ERROR: {label} must be an existing directory under {EVIDENCE_ROOT}",
                file=sys.stderr,
            )
            return 2
    if left == right:
        print("ERROR: input directories must be different", file=sys.stderr)
        return 2

    now = dt.datetime.now().astimezone()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    default_out = EVIDENCE_ROOT / now.strftime("%Y-%m-%d") / "phase-1" / f"evidence-diff-{stamp}"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_out.resolve()
    if not out.is_relative_to(EVIDENCE_ROOT):
        print("ERROR: output directory must be under repository evidence/", file=sys.stderr)
        return 2
    if out in (left, right) or out.is_relative_to(left) or out.is_relative_to(right):
        print("ERROR: output directory cannot be inside an input directory", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)

    left_hashes = files_map(left)
    right_hashes = files_map(right)
    all_paths = sorted(set(left_hashes) | set(right_hashes))
    changes: list[dict[str, object]] = []
    for rel in all_paths:
        lh, rh = left_hashes.get(rel), right_hashes.get(rel)
        if lh is None:
            state = "added_in_right"
        elif rh is None:
            state = "missing_in_right"
        elif lh != rh:
            state = "changed"
        else:
            state = "unchanged"
        changes.append({"path": rel, "status": state, "left_sha256": lh, "right_sha256": rh})

    left_sums = verify_sums(left)
    right_sums = verify_sums(right)
    checksum_fail = left_sums["status"] == "FAIL" or right_sums["status"] == "FAIL"
    different = any(item["status"] != "unchanged" for item in changes)
    if checksum_fail:
        overall = "FAIL"
    elif different or left_sums["status"] == "WARN" or right_sums["status"] == "WARN":
        overall = "DIFFERENCES_FOUND"
    else:
        overall = "NO_DIFFERENCE"

    summary = {
        "left": str(left),
        "right": str(right),
        "left_file_count": len(left_hashes),
        "right_file_count": len(right_hashes),
        "unchanged": sum(1 for x in changes if x["status"] == "unchanged"),
        "changed": sum(1 for x in changes if x["status"] == "changed"),
        "added_in_right": sum(1 for x in changes if x["status"] == "added_in_right"),
        "missing_in_right": sum(1 for x in changes if x["status"] == "missing_in_right"),
        "left_checksums": left_sums,
        "right_checksums": right_sums,
    }
    report = {
        "schema_version": 1,
        "observed_at": now.isoformat(),
        "status": overall,
        "summary": summary,
        "files": changes,
    }
    (out / "diff.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    stdout_lines = [
        "CK-NEXUS evidence diff",
        f"observed_at={now.isoformat()}",
        f"status={overall}",
        f"left={left}",
        f"right={right}",
        f"left_files={len(left_hashes)} right_files={len(right_hashes)}",
        f"unchanged={summary['unchanged']} changed={summary['changed']} "
        f"added_in_right={summary['added_in_right']} "
        f"missing_in_right={summary['missing_in_right']}",
        f"left_sha256sums={left_sums['status']} checked={left_sums['checked']}",
        f"right_sha256sums={right_sums['status']} checked={right_sums['checked']}",
        f"output_dir={out}",
        "",
    ]
    stdout_text = "\n".join(stdout_lines)
    (out / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (out / "stderr.log").write_text("", encoding="utf-8")
    audit = {
        "timestamp": now.isoformat(),
        "action": "read-only comparison; report files created",
        "source_mutated": False,
        "source_directories_modified": False,
        "secrets_recorded": False,
        "rollback": (
            "Remove only this generated output directory after review; input evidence is unchanged."
        ),
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    result = {
        "schema_version": 1,
        "phase": "1-ck-evidence-diff",
        "observed_at": now.isoformat(),
        "status": overall,
        "host": socket.gethostname(),
        "checks": [
            {
                "name": "input_left_sha256sums",
                "status": left_sums["status"],
                "detail": str(left_sums["detail"]),
            },
            {
                "name": "input_right_sha256sums",
                "status": right_sums["status"],
                "detail": str(right_sums["detail"]),
            },
            {
                "name": "evidence_comparison",
                "status": "WARN" if different else "PASS",
                "detail": (
                    f"{summary['changed']} changed, "
                    f"{summary['added_in_right']} added, "
                    f"{summary['missing_in_right']} missing"
                ),
            },
        ],
        "evidence": {
            "stdout": "stdout.log",
            "stderr": "stderr.log",
            "result": "result.json",
            "sha256sums": "SHA256SUMS",
            "audit": "audit.json",
        },
        "audit": {
            "action": "read-only comparison; report files created",
            "source_mutated": False,
            "secrets_recorded": False,
            "rollback": (
                "Remove only this generated output directory after review; "
                "input evidence is unchanged."
            ),
        },
        "rollback_plan": (
            "Comparison does not modify input evidence; remove only the generated "
            "output directory after review if desired."
        ),
        "details": {
            "left": str(left),
            "right": str(right),
            "report": "diff.json",
            "summary": summary,
        },
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name in ("diff.json", "stdout.log", "stderr.log", "result.json", "audit.json"):
        (out / name).chmod(0o600)
    sums = [
        f"{sha256(out / name)}  {name}"
        for name in ("diff.json", "stdout.log", "stderr.log", "result.json", "audit.json")
    ]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (out / "SHA256SUMS").chmod(0o600)
    print(stdout_text, end="")
    print("SHA256SUMS:")
    print("\n".join(sums))
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
