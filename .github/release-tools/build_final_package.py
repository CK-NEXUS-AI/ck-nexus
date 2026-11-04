#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_SOURCE = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
EXPECTED_TREE = "0525195934f703a8becf8a39f6397b2411e0bb2e"
EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, timeout=60
    )
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build checksummed CK-NEXUS production source artifact")
    parser.add_argument("--closure-result", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    closure = json.loads(args.closure_result.read_text(encoding="utf-8"))
    if closure.get("status") not in {"GATES_PASS_PACKAGE_NOT_PROVIDED", "ELIGIBLE_FOR_REVIEW_NOT_MERGED"}:
        raise SystemExit("closure gates are not eligible for packaging")
    if git("show", "-s", "--format=%T", EXPECTED_SOURCE) != EXPECTED_TREE:
        raise SystemExit("runtime source tree mismatch")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tar_path = args.output_dir / "ck-nexus-production-source.tar"
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "--prefix=ck-nexus/", EXPECTED_SOURCE],
        check=True,
        capture_output=True,
        timeout=120,
    ).stdout
    tar_path.write_bytes(archive)
    digest = sha256_file(tar_path)
    manifest = {
        "schema_version": 1,
        "classification": "FINAL_PRODUCTION_PACKAGE_CANDIDATE",
        "production_ready_claim": False,
        "requires_human_release_review": True,
        "source_sha": EXPECTED_SOURCE,
        "source_tree": EXPECTED_TREE,
        "runtime_subject": EXPECTED_SUBJECT,
        "artifact": tar_path.name,
        "artifact_sha256": digest,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = args.output_dir / "FINAL_PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "SHA256SUMS").write_text(f"{digest}  {tar_path.name}\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
