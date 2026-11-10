from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.generate_update_report import (
    RUNTIME_PATHS,
    _combine_status,
    aggregate_progress,
    gate_progress,
    group_states,
    load_gate_states,
    render_report,
)
from scripts.render_badge import COLORS, render_svg


class UpdateReportBadgeTests(unittest.TestCase):
    def _init_source_repo(self, root: Path) -> tuple[str, str]:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        runtime = root / "creator_app" / "runtime.py"
        runtime.parent.mkdir(exist_ok=True)
        runtime.write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "creator_app/runtime.py"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "source"], check=True)
        source_sha = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        source_tree = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True
        ).strip()
        return source_sha, source_tree

    def test_status_mapping_does_not_turn_failure_into_percentage(self) -> None:
        self.assertEqual(gate_progress("PASS"), 100)
        self.assertEqual(gate_progress("PASS_CANDIDATE"), 75)
        self.assertEqual(gate_progress("NOT_STARTED"), 0)
        self.assertIsNone(gate_progress("FAIL"))
        self.assertIsNone(gate_progress("BLOCKED"))
        self.assertIsNone(gate_progress("NOT_VERIFIED"))
        self.assertIsNone(gate_progress("UNKNOWN"))
        self.assertIsNone(gate_progress("STALE"))

    def test_aggregate_is_unknown_if_any_member_has_no_numeric_index(self) -> None:
        self.assertEqual(aggregate_progress([75, 100]), 88)
        self.assertEqual(aggregate_progress([0, 100]), 50)
        self.assertIsNone(aggregate_progress([100, None]))
        self.assertIsNone(aggregate_progress([]))

    def test_q10_uses_gate_result_not_component_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_sha, source_tree = self._init_source_repo(root)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q10_DEPENDENCY_AUDIT.json").write_text(
                json.dumps(
                    {
                        "gate": "Q10",
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "gate_result": "NOT_VERIFIED",
                        "component_result": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            state = load_gate_states(root)["Q10"]
            self.assertEqual(state["status"], "NOT_VERIFIED")
            self.assertIsNone(state["progress"])
            self.assertEqual(state["sources"], ["evidence/Q10_DEPENDENCY_AUDIT.json"])

    def test_q16_requires_both_image_and_license_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_sha, source_tree = self._init_source_repo(root)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q16_PRODUCTION_IMAGE.json").write_text(
                json.dumps(
                    {
                        "gate": "Q16_PRODUCTION_IMAGE",
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "result": "PASS_CANDIDATE",
                    }
                ),
                encoding="utf-8",
            )
            (evidence / "Q16_RUNTIME_LICENSE_SUMMARY.json").write_text(
                json.dumps(
                    {
                        "gate": "Q16_RUNTIME_LICENSES",
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "result": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            state = load_gate_states(root)["Q16"]
            self.assertEqual(state["status"], "PASS_CANDIDATE")
            self.assertEqual(len(state["sources"]), 2)

    def test_evidence_becomes_stale_after_runtime_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_sha, source_tree = self._init_source_repo(root)
            runtime = root / "creator_app" / "runtime.py"
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q10_DEPENDENCY_AUDIT.json").write_text(
                json.dumps(
                    {
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "gate_result": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            runtime.write_text("VALUE = 2\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "creator_app/runtime.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "runtime changed"], check=True)
            state = load_gate_states(root)["Q10"]
            self.assertEqual(state["status"], "STALE")
            self.assertIsNone(state["progress"])

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
        self.assertIn('fill="#1a7f37"', svg)

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
        self.assertIn("git rev-list --count origin/main..FETCH_HEAD", workflow)
        self.assertIn("branch_ahead", workflow)
        self.assertIn("ahead != '0'", workflow)

    def test_workflow_never_force_pushes_or_overwrites_remote_branch(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text()
        self.assertIn("git merge --no-edit origin/main", workflow)
        push_commands = re.findall(r"(?m)^\s*git\s+push\b[^\n]*$", workflow)
        self.assertTrue(push_commands)
        force_pattern = re.compile(
            r"(?i)(?:^|\s)-f(?:\s|$)|--force(?:-with-lease)?(?:=|\s|$)|(?:^|\s)\+[^ \t]+"
        )
        for command in push_commands:
            self.assertNotRegex(command, force_pattern)
        for unsafe in (
            "git push -f origin HEAD:main",
            "git push --force origin HEAD:main",
            "git push --force-with-lease origin HEAD:main",
            "git push origin +refs/heads/work:refs/heads/main",
        ):
            self.assertRegex(unsafe, force_pattern)

    def test_workflow_skips_ci_and_does_not_trigger_on_automation_branch(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text()
        self.assertIn("[skip ci]", workflow)
        self.assertIn("branches:\n      - main", workflow)
        self.assertNotIn("- automation/gate-progress", workflow)

    def test_unknown_member_prevents_candidate_aggregation(self) -> None:
        self.assertEqual(_combine_status(["PASS_CANDIDATE", "UNKNOWN"]), "UNKNOWN")

    def test_unknown_evidence_is_not_hidden_by_not_started_member(self) -> None:
        self.assertEqual(_combine_status(["NOT_STARTED", "UNKNOWN"]), "UNKNOWN")

    def test_q16_missing_runtime_license_evidence_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_sha, source_tree = self._init_source_repo(root)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q16_PRODUCTION_IMAGE.json").write_text(
                json.dumps(
                    {
                        "gate": "Q16_PRODUCTION_IMAGE",
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "result": "PASS_CANDIDATE",
                    }
                ),
                encoding="utf-8",
            )
            state = load_gate_states(root)["Q16"]
            self.assertEqual(state["status"], "UNKNOWN")
            self.assertIsNone(state["progress"])
            self.assertEqual(state["sources"], ["evidence/Q16_PRODUCTION_IMAGE.json"])

    def test_invalid_utf8_evidence_is_unknown_not_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q10_DEPENDENCY_AUDIT.json").write_bytes(bytes([0xFF, 0xFE]))
            state = load_gate_states(root)["Q10"]
            self.assertEqual(state["status"], "UNKNOWN")
            self.assertIsNone(state["progress"])

    def test_not_started_group_progress_is_zero(self) -> None:
        gates = {
            "Q10": {"status": "PASS", "progress": 100},
            "Q11": {"status": "PASS", "progress": 100},
            "Q12": {"status": "PASS", "progress": 100},
            "Q13": {"status": "PASS", "progress": 100},
            "Q14": {"status": "PASS", "progress": 100},
            "Q15": {"status": "NOT_STARTED", "progress": 0},
            "Q16": {"status": "PASS", "progress": 100},
        }
        delivery = group_states(gates)["Delivery"]
        self.assertEqual(delivery["status"], "NOT_STARTED")
        self.assertEqual(delivery["progress"], 0)

    def test_report_is_deterministic_when_git_head_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._init_source_repo(root)
            first = render_report(root)
            subprocess.run(
                ["git", "-C", str(root), "commit", "--allow-empty", "-qm", "unrelated commit"],
                check=True,
            )
            second = render_report(root)
            self.assertEqual(first, second)

    def test_config_capability_catalog_is_an_evidence_runtime_path(self) -> None:
        self.assertIn("config", RUNTIME_PATHS)

    def test_config_change_marks_bound_evidence_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._init_source_repo(root)
            config = root / "config" / "capability_catalog.json"
            config.parent.mkdir()
            config.write_text('{"capabilities": []}' + "\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "config/capability_catalog.json"],
                check=True,
            )
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "config source"], check=True)
            source_sha = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip()
            source_tree = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True
            ).strip()
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "Q10_DEPENDENCY_AUDIT.json").write_text(
                json.dumps(
                    {
                        "source_sha": source_sha,
                        "source_tree": source_tree,
                        "gate_result": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            config.write_text('{"capabilities": ["changed"]}' + "\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "config/capability_catalog.json"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "runtime config changed"],
                check=True,
            )
            self.assertEqual(load_gate_states(root)["Q10"]["status"], "STALE")

    def test_badge_status_colors_meet_wcag_aa_for_white_text(self) -> None:
        def luminance(value: str) -> float:
            channels = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        for status, color in COLORS.items():
            ratio = (luminance("#ffffff") + 0.05) / (luminance(color) + 0.05)
            self.assertGreaterEqual(ratio, 4.5, f"{status} contrast is {ratio:.2f}:1")

    def test_readme_explains_badge_group_indices_and_stale_conditions(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("![Security gate Q10 status badge]", readme)
        self.assertIn("arithmetic mean", readme)
        self.assertIn("source commit is missing", readme)
        self.assertIn("runtime-path changes", readme)

    def test_workflow_runs_generator_before_automation_branch_checkout(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        self.assertLess(
            workflow.index("Generate update report"),
            workflow.index("Prepare automation branch"),
        )
        self.assertIn("trusted main", workflow.lower())

    def test_workflow_scopes_write_permissions_by_job(self) -> None:
        workflow = yaml.safe_load(
            Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        )
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        jobs = workflow["jobs"]
        self.assertEqual(jobs["render"]["permissions"], {"contents": "write"})
        self.assertEqual(
            jobs["create-pr"]["permissions"],
            {"contents": "read", "pull-requests": "write"},
        )
        self.assertEqual(jobs["lint-workflow"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["verify-docs"]["permissions"], {"contents": "read"})

    def test_workflow_uses_separate_concurrency_groups(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        self.assertIn("auto-update-gate-progress-render", workflow)
        self.assertIn("auto-update-gate-progress-lint", workflow)

    def test_workflow_limits_conflict_resolution_to_generated_artifacts(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        self.assertIn("git diff --name-only --diff-filter=U", workflow)
        self.assertIn("git checkout --theirs", workflow)
        self.assertIn("unexpected merge conflict", workflow.lower())

    def test_write_jobs_only_run_from_main_ref(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(
            workflow.count("github.ref == 'refs/heads/main'"),
            2,
        )
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertLess(
            workflow.index('git config user.name "github-actions[bot]"'),
            workflow.index("git merge --no-edit origin/main"),
        )

    def test_workflow_refuses_non_generated_files_on_automation_branch(self) -> None:
        workflow = Path(".github/workflows/auto-update.yml").read_text(encoding="utf-8")
        self.assertIn("git diff --name-only origin/main...FETCH_HEAD", workflow)
        self.assertIn("Unexpected non-generated path in automation branch", workflow)
        self.assertIn('if [[ -z "$files" ]]; then', workflow)
        self.assertIn("ahead=0", workflow)


if __name__ == "__main__":
    unittest.main()
