from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_CONTROLS = {f"CKAG-{index:02d}" for index in range(1, 11)}
ALLOWED_ACTIONS = {"DENY", "QUARANTINE", "ESCALATE"}
REQUIRED_REFERENCES = {
    "OWASP GenAI LLM Top 10 2026",
    "OWASP Top 10 for Agentic Applications 2026",
    "OWASP Agent Control Standard 2026",
}


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(path: str | Path) -> list[str]:
    data = _load(path)
    errors: list[str] = []
    authority = data.get("authority", {})
    if authority.get("self_approval") is not False:
        errors.append("self_approval must be false")
    if authority.get("production_mutation") is not False:
        errors.append("production_mutation must be false")
    if authority.get("independent_verification_required") is not True:
        errors.append("independent verification must be required")

    references = set(data.get("normative_references", []))
    missing_references = sorted(REQUIRED_REFERENCES - references)
    if missing_references:
        errors.append("missing normative references: " + ", ".join(missing_references))

    required_threats = set(data.get("required_threat_families", []))
    allowed_hooks = set(data.get("allowed_runtime_hooks", []))
    controls = data.get("controls", [])
    ids = [control.get("id") for control in controls]
    missing_controls = sorted(REQUIRED_CONTROLS - set(ids))
    if missing_controls:
        errors.append("missing controls: " + ", ".join(missing_controls))
    if len(ids) != len(set(ids)):
        errors.append("duplicate control ids")

    covered_threats: set[str] = set()
    for control in controls:
        control_id = str(control.get("id", "<missing>"))
        threats = set(control.get("threat_families", []))
        hooks = set(control.get("runtime_hooks", []))
        covered_threats.update(threats)
        if not threats:
            errors.append(f"{control_id}: threat_families required")
        if not hooks:
            errors.append(f"{control_id}: runtime_hooks required")
        unknown_hooks = sorted(hooks - allowed_hooks)
        if unknown_hooks:
            errors.append(f"{control_id}: unknown hooks: {', '.join(unknown_hooks)}")
        if control.get("fail_closed") is not True:
            errors.append(f"{control_id}: fail_closed must be true")
        if control.get("default_action") not in ALLOWED_ACTIONS:
            errors.append(f"{control_id}: unsafe default_action")
        if control.get("evidence_required") is not True:
            errors.append(f"{control_id}: evidence_required must be true")
        mappings = set(control.get("mappings", []))
        if "OWASP-ACS-2026" not in mappings:
            errors.append(f"{control_id}: OWASP ACS mapping required")

    uncovered = sorted(required_threats - covered_threats)
    if uncovered:
        errors.append("uncovered threat families: " + ", ".join(uncovered))
    if data.get("status") == "VERIFIED":
        errors.append("profile cannot self-declare VERIFIED")
    return errors


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "config/agent_security_governance_2026.json"
    errors = validate(path)
    if errors:
        print("FAIL")
        print("\n".join(errors))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
