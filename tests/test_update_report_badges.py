from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_update_report import (
    aggregate_progress,
    gate_progress,
    group_states,
    load_gate_states,
)
from scripts.render_badge import render_svg


class UpdateReportBadgeTests(unittest.TestCase):
    def test_status_mapping_does_not_turn_failure_into_percentage(self) -> None:
        self.assertEqual(gate_progress("PASS"), 100)
        self.assertEqual(gate_progress("PASS_CANDIDATE"), 75)
        self.assertEqual(gate_progress("NOT_STARTED"), 0)
        self.assertIsNone(gate_progress("FAIL"))
        self.assertIsNone(gate_progress("BLOCKED"))
        self.assertIsNone(gate_progress("NOT_VERIFIED"))
        self.assertIsNone(gate_progress("UNKNOWN"))

    def test_aggregate_is_unknown_if_any_member_has_no_numeric_index(self) -> None:
        self.assertEqual(aggregate_progress([75, 100]), 88)
        self.assertEqual(aggregate_progress([0, 100]), 50)
        self.assertIsNone(aggregate_progress([100, None]))
        self.assertIsNone(aggregate_progress([]))

    def test_q10_uses_gate_result_not_component_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q10_DEPENDENCY_AUDIT.json").write_text(
                json.dumps({
                    "gate": "Q10",
                    "gate_result": "NOT_VERIFIED",
                    "component_result": "PASS",
                }),
                encoding="utf-8",
            )
            state = load_gate_states(root)["Q10"]
            self.assertEqual(state["status"], "NOT_VERIFIED")
            self.assertIsNone(state["progress"])
            self.assertEqual(state["sources"], ["evidence/Q10_DEPENDENCY_AUDIT.json"])

    def test_q16_requires_both_image_and_license_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q16_PRODUCTION_IMAGE.json").write_text(
                json.dumps({"gate": "Q16_PRODUCTION_IMAGE", "result": "PASS_CANDIDATE"}),
                encoding="utf-8",
            )
            (evidence / "Q16_RUNTIME_LICENSE_SUMMARY.json").write_text(
                json.dumps({"gate": "Q16_RUNTIME_LICENSES", "result": "PASS"}),
                encoding="utf-8",
            )
            state = load_gate_states(root)["Q16"]
            self.assertEqual(state["status"], "PASS_CANDIDATE")
            self.assertEqual(len(state["sources"]), 2)

    def test_missing_evidence_is_unknown_not_zero_or_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = load_gate_states(Path(directory))["Q10"]
            self.assertEqual(state["status"], "UNKNOWN")
            self.assertIsNone(state["progress"])

    def test_badge_renders_fail_as_label_with_red_state(self) -> None:
        svg = render_svg("Security", "FAIL", None)
        self.assertIn('width="240" height="28"', svg)
        self.assertIn('fill="#cf222e"', svg)
        self.assertIn(">FAIL</text>", svg)
        self.assertNotIn("1%", svg)

    def test_badge_renders_blocked_as_label_not_percentage(self) -> None:
        svg = render_svg("Stability", "BLOCKED", None)
        self.assertIn(">BLOCKED</text>", svg)
        self.assertNotIn("%</text>", svg)

    def test_pass_badge_is_100_percent(self) -> None:
        svg = render_svg("Delivery", "PASS", 100)
        self.assertIn(">100%</text>", svg)
        self.assertIn('fill="#2ea043"', svg)

    def test_group_status_preserves_blocked_state(self) -> None:
        gates = {
            "Q10": {"status": "PASS", "progress": 100},
            "Q11": {"status": "BLOCKED", "progress": None},
            "Q12": {"status": "PASS", "progress": 100},
            "Q13": {"status": "PASS", "progress": 100},
            "Q14": {"status": "PASS", "progress": 100},
            "Q15": {"status": "PASS", "progress": 100},
            "Q16": {"status": "PASS", "progress": 100},
        }
        self.assertEqual(group_states(gates)["Stability"]["status"], "BLOCKED")
        self.assertIsNone(group_states(gates)["Stability"]["progress"])

    def test_workflow_has_no_push_pr_or_verify_on_no_diff(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text()
        self.assertIn('echo "changed=false" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("needs.render.outputs.changed == 'true'", workflow)
        self.assertIn('process.env.CHANGED !== "true"', workflow)

    def test_workflow_never_force_pushes_or_overwrites_remote_branch(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text()
        self.assertIn("git merge --no-edit origin/main", workflow)
        self.assertNotIn("git push --force", workflow)
        self.assertNotIn("--force-with-lease", workflow)

    def test_workflow_skips_ci_and_does_not_trigger_on_automation_branch(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text()
        self.assertIn("[skip ci]", workflow)
        self.assertIn("branches:\n      - main", workflow)
        self.assertNotIn("- automation/gate-progress", workflow)


if __name__ == "__main__":
    unittest.main()
