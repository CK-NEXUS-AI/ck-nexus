from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "ai_factory.json").read_text(encoding="utf-8"))


def score(metrics: dict[str, float]) -> dict[str, object]:
    weights = CONFIG["weights"]
    total = 0.0
    dimensions = {}
    for name, weight in weights.items():
        raw = float(metrics.get(name, 0.0))
        value = max(0.0, min(100.0, raw))
        contribution = value * float(weight) / 100.0
        dimensions[name] = {
            "score": value,
            "weight": weight,
            "contribution": contribution,
        }
        total += contribution

    if metrics.get("independent_verification", 0) < 100:
        status = "UNVERIFIED"
    elif total < CONFIG["promotion"]["development"]:
        status = "REJECT"
    elif total < CONFIG["promotion"]["release_candidate"]:
        status = "DEVELOPMENT"
    elif total < CONFIG["promotion"]["high_quality"]:
        status = "RELEASE_CANDIDATE"
    elif total < CONFIG["promotion"]["premium"]:
        status = "HIGH_QUALITY"
    else:
        status = "PREMIUM"

    return {
        "schema_version": 1,
        "kind": "CKNEXUS_AI_FACTORY_SCORE",
        "score": round(total, 2),
        "status": status,
        "dimensions": dimensions,
        "laws": [
            "SCORE != VERIFIED",
            "TEST != PRODUCTION",
            "AI_CLAIM != EVIDENCE",
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ai_factory_score.py METRICS_JSON", file=sys.stderr)
        return 2
    metrics = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = score(metrics)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
