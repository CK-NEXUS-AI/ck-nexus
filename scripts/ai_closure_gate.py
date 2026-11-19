from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = (
    "implementation_evidence",
    "test_evidence",
    "security_evidence",
    "independent_verification",
    "provenance",
)


def evaluate(record: dict) -> dict:
    missing = [name for name in REQUIRED if not record.get(name)]
    regression = bool(record.get("regression_increased", False))
    production = bool(record.get("production_mutation", False))
    verified = not missing and not regression and not production

    if verified:
        status = "CLOSED"
    elif record.get("blocked_task"):
        status = "BLOCKED_TASK"
    else:
        status = "REPAIR_REQUIRED"

    return {
        "schema_version": 1,
        "status": status,
        "missing_evidence": missing,
        "regression_increased": regression,
        "production_mutation": production,
        "laws": [
            "NO_EVIDENCE_NO_DONE",
            "NO_INDEPENDENT_VERIFICATION_NO_DONE",
            "SCORE_IS_NOT_VERIFICATION",
            "FAILED_ATTEMPTS_ARE_KNOWLEDGE",
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ai_closure_gate.py RECORD.json", file=sys.stderr)
        return 2
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(evaluate(record), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
