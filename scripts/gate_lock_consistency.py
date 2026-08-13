from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = ("gateway", "dev", "billing", "email", "github-app")


def required_names(pyproject_path: Path, groups: tuple[str, ...]) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})
    missing_groups = sorted(group for group in groups if group not in optional)
    if missing_groups:
        raise ValueError("unknown optional dependency group(s): " + ", ".join(missing_groups))

    raw = list(project.get("dependencies", []))
    for group in groups:
        raw.extend(optional[group])
    return {Requirement(item).name.lower() for item in raw}


def locked_names(lock_path: Path) -> set[str]:
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = data.get("package", [])
    return {str(item.get("name", "")).lower() for item in packages if item.get("name")}


def evaluate(
    pyproject_path: Path, lock_path: Path, groups: tuple[str, ...]
) -> tuple[set[str], set[str]]:
    required = required_names(pyproject_path, groups)
    locked = locked_names(lock_path)
    return required, required - locked


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed when uv.lock omits direct CK-NEXUS runtime or gate dependencies."
    )
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml")
    parser.add_argument("--lock", type=Path, default=ROOT / "uv.lock")
    parser.add_argument("--groups", nargs="*", default=list(DEFAULT_GROUPS))
    args = parser.parse_args()

    try:
        required, missing = evaluate(args.pyproject, args.lock, tuple(args.groups))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"[FAIL] lock consistency: {exc}")
        return 2

    if missing:
        print("[FAIL] uv.lock missing required package(s): " + ", ".join(sorted(missing)))
        print(
            f"Lock consistency: {len(required) - len(missing)}/{len(required)} required packages present"
        )
        return 1

    print(f"[PASS] uv.lock contains all {len(required)} required direct packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
