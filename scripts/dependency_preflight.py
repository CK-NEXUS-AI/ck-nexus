from __future__ import annotations

import argparse
import importlib.metadata
import tomllib
from dataclasses import dataclass
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = ("gateway", "dev", "billing", "email", "github-app")


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    requirement: str
    installed_version: str | None
    satisfied: bool
    detail: str


def load_requirements(pyproject_path: Path, groups: tuple[str, ...]) -> list[Requirement]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    raw: list[str] = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    missing_groups = [group for group in groups if group not in optional]
    if missing_groups:
        raise ValueError("unknown optional dependency group(s): " + ", ".join(missing_groups))
    for group in groups:
        raw.extend(optional[group])

    unique: dict[str, Requirement] = {}
    for item in raw:
        req = Requirement(item)
        unique[req.name.lower()] = req
    return [unique[name] for name in sorted(unique)]


def check_requirement(req: Requirement) -> DependencyStatus:
    try:
        version = importlib.metadata.version(req.name)
    except importlib.metadata.PackageNotFoundError:
        return DependencyStatus(str(req), None, False, "not installed")

    if req.specifier and version not in req.specifier:
        return DependencyStatus(
            str(req), version, False, f"installed {version} does not satisfy {req.specifier}"
        )
    return DependencyStatus(str(req), version, True, f"installed {version}")


def evaluate(pyproject_path: Path, groups: tuple[str, ...]) -> list[DependencyStatus]:
    return [check_requirement(req) for req in load_requirements(pyproject_path, groups)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify CK-NEXUS direct runtime and production-gate dependencies offline."
    )
    parser.add_argument(
        "--pyproject", type=Path, default=ROOT / "pyproject.toml", help="pyproject.toml path"
    )
    parser.add_argument(
        "--groups",
        nargs="*",
        default=list(DEFAULT_GROUPS),
        help="optional dependency groups required for verification",
    )
    args = parser.parse_args()

    try:
        statuses = evaluate(args.pyproject, tuple(args.groups))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"[FAIL] dependency manifest: {exc}")
        return 2

    failed = [item for item in statuses if not item.satisfied]
    for item in statuses:
        state = "PASS" if item.satisfied else "FAIL"
        print(f"[{state}] {item.requirement}: {item.detail}")

    print(
        f"Dependency preflight: {len(statuses) - len(failed)}/{len(statuses)} satisfied; "
        f"{len(failed)} missing/incompatible"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
