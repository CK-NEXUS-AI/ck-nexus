"""Regression tests for fail-closed release readiness reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_external_gates_without_current_subject_evidence_are_blocked() -> None:
    process = subprocess.run(
        [sys.executable, "scripts/production_readiness.py", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    result = json.loads(process.stdout)
    gates = {gate["id"]: gate for gate in result["gates"]}

    for gate_id in ("Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q16"):
        assert gates[gate_id]["state"] == "BLOCKED"

    assert result["production_eligible"] is False


def test_q13_to_q16_explain_exact_subject_evidence_requirements() -> None:
    process = subprocess.run(
        [sys.executable, "scripts/production_readiness.py", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    gates = {gate["id"]: gate for gate in json.loads(process.stdout)["gates"]}

    assert "exact release subject" in gates["Q13"]["evidence"]
    assert "operator-alert receipt" in gates["Q14"]["evidence"]
    assert "fresh supported machine" in gates["Q15"]["evidence"]
    assert "Q10-Q15" in gates["Q16"]["evidence"]
