from __future__ import annotations

import argparse
from enum import StrEnum
from pathlib import Path


class CiLane(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    RELEASE_EVIDENCE = "RELEASE_EVIDENCE"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"


_DEVELOPMENT_HEAD_PREFIXES = (
    "post-p0/",
    "feat/",
    "research/",
    "dev/",
    "docs/",
    "ui/",
    "arch/",
    "ci/",
)

_RELEASE_BOUND_PREFIXES = (
    "release/",
    "verify/",
    "prepare/",
    "prep/",
    "q10/",
    "ops/",
)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _is_development_ref(ref_name: str) -> bool:
    return ref_name.startswith(_DEVELOPMENT_HEAD_PREFIXES) or ref_name.startswith("fix/pr46-")


def _is_release_ref(ref_name: str) -> bool:
    return (
        ref_name == "main"
        or ref_name.startswith(_RELEASE_BOUND_PREFIXES)
        or ref_name.startswith("fix/q")
    )


def classify_ci_lane(
    *,
    event_name: str,
    head_ref: str = "",
    base_ref: str = "",
    ref_name: str = "",
) -> CiLane:
    """Classify CI evidence semantics without guessing unknown branches."""

    event_name = _clean(event_name)
    head_ref = _clean(head_ref)
    base_ref = _clean(base_ref)
    ref_name = _clean(ref_name)

    if event_name != "pull_request":
        if _is_development_ref(ref_name):
            return CiLane.DEVELOPMENT
        if _is_release_ref(ref_name):
            return CiLane.RELEASE_EVIDENCE
        return CiLane.BLOCKED_UNKNOWN

    if base_ref.startswith("post-p0/"):
        return CiLane.DEVELOPMENT

    if _is_development_ref(head_ref):
        return CiLane.DEVELOPMENT

    if base_ref.startswith("release/"):
        return CiLane.RELEASE_EVIDENCE

    if _is_release_ref(head_ref):
        return CiLane.RELEASE_EVIDENCE

    return CiLane.BLOCKED_UNKNOWN


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify CK-NEXUS CI evidence lane")
    parser.add_argument("--event", required=True)
    parser.add_argument("--head", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--ref", default="")
    parser.add_argument("--github-output")
    return parser


def main() -> int:
    args = _parser().parse_args()
    lane = classify_ci_lane(
        event_name=args.event,
        head_ref=args.head,
        base_ref=args.base,
        ref_name=args.ref,
    )
    print(lane.value)
    if args.github_output:
        output_path = Path(args.github_output)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(f"lane={lane.value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
