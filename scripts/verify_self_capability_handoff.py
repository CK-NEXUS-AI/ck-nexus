from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "creator_app/core/self_capability_manager.py",
    "creator_app/ai_team/universal_system.py",
    "creator_app/agnes/mcp_server.py",
    "start_all.sh",
    "run_anyclaw.py",
)

TEST_CANDIDATES = (
    "tests/test_team.py",
    "tests/test_universal.py",
)


@dataclass(frozen=True, slots=True)
class FileEvidence:
    path: str
    present: bool
    size: int | None
    sha256: str | None


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _evidence(relative_path: str) -> FileEvidence:
    path = ROOT / relative_path
    if not path.is_file():
        return FileEvidence(relative_path, False, None, None)
    return FileEvidence(relative_path, True, path.stat().st_size, _digest(path))


def _discover_team_tests() -> list[str]:
    discovered = [path for path in TEST_CANDIDATES if (ROOT / path).is_file()]
    package_tests = ROOT / "creator_app" / "ai_team" / "tests"
    if package_tests.is_dir():
        discovered.extend(
            str(path.relative_to(ROOT))
            for path in sorted(package_tests.glob("test_*.py"))
            if path.is_file()
        )
    return sorted(set(discovered))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the local SelfCapability/AI-Team handoff is present in canonical source."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    files = [_evidence(path) for path in REQUIRED_PATHS]
    tests = _discover_team_tests()
    missing = [item.path for item in files if not item.present]

    tracked_env = [
        path
        for path in (".env", ".env.local", ".env.production")
        if (ROOT / path).exists()
    ]

    status = "PASS" if not missing and tests and not tracked_env else "BLOCKED"
    result = {
        "status": status,
        "production_evidence": False,
        "scope": "POST_P0_SELF_CAPABILITY_RECONCILIATION",
        "files": [asdict(item) for item in files],
        "missing_required_paths": missing,
        "discovered_tests": tests,
        "forbidden_env_files_present": tracked_env,
        "production_status": "NO-GO",
        "notes": [
            "Local-only claims do not become canonical until source is committed and CI passes.",
            "This verifier cannot satisfy or promote Q10, Q11, or Q12.",
        ],
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"handoff_status={status}")
        print(f"missing={missing}")
        print(f"tests={tests}")
        print(f"forbidden_env_files_present={tracked_env}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
