from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CATALOG = Path(__file__).resolve().parents[1] / "capabilities" / "system-skills.catalog.json"
VALID_DECISIONS = {
    "REUSE",
    "EXTEND",
    "NEW_SKILL",
    "EVALUATE",
    "BLOCKED_BY_EVIDENCE",
    "REJECT",
}
AUTO_SAFE_RISKS = {"read_only", "local_reversible"}


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    skill_id: str
    decision: str
    auto_safe: bool
    next_action: str
    reason: str


def load_catalog(path: Path = CATALOG) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    skills = raw.get("skills", [])
    ids = [str(item.get("id", "")) for item in skills]
    if not skills or any(not item for item in ids):
        raise ValueError("catalog requires non-empty skill ids")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate skill ids")
    for item in skills:
        if item.get("decision") not in VALID_DECISIONS:
            raise ValueError(f"invalid decision for {item['id']}")
        if not item.get("evidence"):
            raise ValueError(f"missing evidence for {item['id']}")
    return raw


def decide(skill: dict[str, Any]) -> AdmissionDecision:
    decision = str(skill["decision"])
    risk = str(skill.get("risk", "guarded"))
    skill_id = str(skill["id"])
    if decision in {"BLOCKED_BY_EVIDENCE", "REJECT"}:
        return AdmissionDecision(
            skill_id,
            decision,
            False,
            "STOP",
            "evidence or policy blocks adoption",
        )
    if decision == "REUSE":
        return AdmissionDecision(
            skill_id,
            decision,
            risk in AUTO_SAFE_RISKS,
            "REUSE_CANONICAL",
            "canonical capability already exists",
        )
    if decision == "EXTEND":
        return AdmissionDecision(
            skill_id,
            decision,
            risk in AUTO_SAFE_RISKS,
            "EXTEND_IN_DEV",
            "extend existing capability without replacement",
        )
    if decision in {"NEW_SKILL", "EVALUATE"}:
        return AdmissionDecision(
            skill_id,
            decision,
            risk in AUTO_SAFE_RISKS,
            "EVALUATE_IN_DEV",
            "must prove measurable delta before canonical adoption",
        )
    return AdmissionDecision(skill_id, decision, False, "STOP", "unknown state")


def plan(path: Path = CATALOG) -> list[AdmissionDecision]:
    catalog = load_catalog(path)
    return [decide(item) for item in catalog["skills"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--skill")
    parser.add_argument("--auto-safe", action="store_true")
    args = parser.parse_args()
    decisions = plan(args.catalog)
    if args.skill:
        decisions = [item for item in decisions if item.skill_id == args.skill]
        if not decisions:
            raise SystemExit(f"unknown skill: {args.skill}")
    if args.auto_safe:
        decisions = [
            item for item in decisions if item.auto_safe and item.next_action != "STOP"
        ]
    print(json.dumps([asdict(item) for item in decisions], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
