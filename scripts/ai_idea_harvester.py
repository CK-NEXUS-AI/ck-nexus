from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "ai_factory" / "ideas.jsonl"
CONFIG = ROOT / "config" / "ai_product_factory.json"


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def fingerprint(idea: dict) -> str:
    canonical = {
        "problem": normalize(str(idea.get("problem", ""))),
        "target_user": normalize(str(idea.get("target_user", ""))),
        "solution": normalize(str(idea.get("solution", ""))),
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def score_opportunity(idea: dict, weights: dict[str, int]) -> float:
    total = 0.0
    for name, weight in weights.items():
        raw = max(0.0, min(100.0, float(idea.get(name, 0))))
        total += raw * weight / 100.0
    return round(total, 2)


def classify(score: float, thresholds: dict[str, int]) -> str:
    if score >= thresholds["build_now"]:
        return "BUILD_NOW"
    if score >= thresholds["priority"]:
        return "PRIORITY"
    if score >= thresholds["experiment"]:
        return "EXPERIMENT"
    if score >= thresholds["backlog"]:
        return "BACKLOG"
    return "ARCHIVE"


def ingest(idea: dict) -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    weights = config["opportunity"]["weights"]
    thresholds = config["opportunity"]["thresholds"]
    record = dict(idea)
    record["schema_version"] = 1
    record["captured_at"] = datetime.now(UTC).isoformat()
    record["idea_id"] = record.get("idea_id") or "idea-" + fingerprint(record)[:16]
    record["fingerprint"] = fingerprint(record)
    record["provenance_required"] = True
    record["opportunity_score"] = score_opportunity(record, weights)
    record["queue"] = classify(record["opportunity_score"], thresholds)
    record["value_preservation"] = {
        "raw_input_retained": True,
        "failed_methods_retained": True,
        "history_required": True,
    }
    return record


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ai_idea_harvester.py IDEA.json", file=sys.stderr)
        return 2
    idea = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    record = ingest(idea)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
