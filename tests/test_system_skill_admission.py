from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system_skill_admission.py"
SPEC = importlib.util.spec_from_file_location("system_skill_admission", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class SystemSkillAdmissionTests(unittest.TestCase):
    def test_catalog_is_valid_and_unique(self):
        catalog = module.load_catalog(
            ROOT / "capabilities" / "system-skills.catalog.json"
        )
        ids = [item["id"] for item in catalog["skills"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 25)

    def test_failed_lineage_is_fail_closed(self):
        decisions = {item.skill_id: item for item in module.plan()}
        blocked = (
            "failure_memory",
            "durable_execution_v3",
            "agnes_triad_parallel_scheduler",
        )
        for skill_id in blocked:
            self.assertEqual(decisions[skill_id].next_action, "STOP")
            self.assertFalse(decisions[skill_id].auto_safe)

    def test_guarded_skill_never_auto_safe(self):
        decisions = {item.skill_id: item for item in module.plan()}
        self.assertFalse(decisions["human_gate_manager"].auto_safe)
        self.assertFalse(decisions["tool_permission_compiler"].auto_safe)

    def test_read_only_delta_can_be_evaluated_in_dev(self):
        decisions = {item.skill_id: item for item in module.plan()}
        scout = decisions["research_delta_scout"]
        self.assertTrue(scout.auto_safe)
        self.assertEqual(scout.next_action, "EVALUATE_IN_DEV")

    def test_canonical_skill_is_reused(self):
        decisions = {item.skill_id: item for item in module.plan()}
        selector = decisions["pattern_selection_router"]
        self.assertEqual(selector.next_action, "REUSE_CANONICAL")


if __name__ == "__main__":
    unittest.main()
