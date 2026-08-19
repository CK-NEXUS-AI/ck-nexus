from __future__ import annotations

import argparse
import json
from pathlib import Path

SUBJECT_BOUND_EVIDENCE = (
    "evidence/Q05_MULTILANE.json",
    "evidence/Q08_LIVE.json",
    "evidence/Q09_GOVERNANCE_BINDING.json",
    "evidence/Q10_DEPENDENCY_AUDIT.json",
    "evidence/Q11_OPENAI_LIVE.json",
    "evidence/Q12_CGROUP_V2.json",
    "evidence/Q13_POSTGRES_DR.json",
    "evidence/Q14_OBSERVABILITY_ALERT.json",
    "evidence/Q15_CLEAN_MACHINE.json",
    "evidence/Q16_PRODUCTION_IMAGE.json",
    "evidence/Q16_RUNTIME_LICENSE_SUMMARY.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a dry-run invalidation plan when the frozen runtime subject rotates"
    )
    parser.add_argument("--old-subject", required=True)
    parser.add_argument("--new-subject", required=True)
    parser.add_argument("--new-source-sha", required=True)
    parser.add_argument("--new-source-tree", required=True)
    parser.add_argument("--output", default="subject-rotation-plan.json", type=Path)
    args = parser.parse_args()

    if args.old_subject == args.new_subject:
        raise SystemExit("old and new subjects are identical; rotation is not required")

    plan = {
        "schema_version": 1,
        "mode": "DRY_RUN_ONLY",
        "old_subject": args.old_subject,
        "new_subject": args.new_subject,
        "new_source_sha": args.new_source_sha,
        "new_source_tree": args.new_source_tree,
        "invalidate": list(SUBJECT_BOUND_EVIDENCE),
        "restart_from": "Q10",
        "required_order": [
            "Q10 native Codex Security Deep Security Scan",
            "Q11 live provider verification",
            "Q12 delegated cgroup v2 enforcement",
            "Release evidence provenance",
            "Final Production Package",
        ],
        "automatic_mutation_performed": False,
        "production_ready": False,
    }
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
