from __future__ import annotations

import json
from pathlib import Path


def load(name: str) -> dict[str, object]:
    return json.loads(Path("evidence", name).read_text(encoding="utf-8"))


def main() -> int:
    q10 = load("Q10_DEPENDENCY_AUDIT.json")
    q11 = load("Q11_OPENAI_LIVE.json")
    q12 = load("Q12_CGROUP_V2.json")

    if not (
        q10.get("gate_result") == "PASS"
        and q10.get("codex_security_deep_scan") == "PASS"
        and q10.get("production_promotion_allowed") is True
    ):
        action = "Q10_NATIVE_DEEP_SCAN"
    elif not (
        q11.get("result") == "PASS"
        and q11.get("production_promotion_allowed") is True
        and q11.get("credential_exposed") is False
    ):
        action = "Q11_AUTHORIZED_LIVE_PROVIDER"
    elif not (
        q12.get("result") == "PASS"
        and q12.get("actual_kernel_enforcement") is True
        and q12.get("production_promotion_allowed") is True
    ):
        action = "Q12_DELEGATED_CGROUP_V2"
    else:
        action = "RECONCILE_PROVENANCE_THEN_FINAL_PACKAGE"

    report = {
        "schema_version": 1,
        "next_safe_action": action,
        "automatic_external_execution": False,
        "reason": "Live provider execution, self-hosted runner execution and production packaging must remain fail-closed and subject-bound.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
