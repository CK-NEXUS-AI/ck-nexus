from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.release_subject import (
    APPLICATION_PATHS,
    RUNTIME_PATHS,
    calculate_release_subject,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_subject.py"


class ReleaseSubjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "CK-NEXUS Subject Test")
        self.git("config", "user.email", "subject-test@example.invalid")
        files = {
            "app/service.py": "VALUE = 1\n",
            "creator_app/api.py": "API = True\n",
            "services/api.py": "SERVICE = True\n",
            "gateway/app.py": "GATEWAY = True\n",
            "orchestration/controller.py": "CONTROL = True\n",
            "idea_engine/engine.py": "ENGINE = True\n",
            "migrations/001.sql": "SELECT 1;\n",
            "deploy/service.yml": "service: test\n",
            "observability/alerts.yml": "alerts: []\n",
            "Dockerfile": "FROM scratch\n",
            "docker-compose.prod.yml": "services: {}\n",
            "main.py": "def main(): pass\n",
            "pyproject.toml": "[project]\nname='test'\n",
            "uv.lock": "version = 1\n",
            "tests/test_sample.py": "def test_sample(): assert True\n",
            "scripts/helper.py": "VALUE = 2\n",
            "docs/release.md": "historical notes\n",
        }
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "initial subject fixture")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def commit_all(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def test_runtime_matches_legacy_workflow_byte_for_byte(self) -> None:
        legacy = subprocess.check_output(
            ["git", "-C", str(self.repo), "ls-tree", "-r", "HEAD", "--", *RUNTIME_PATHS]
        )
        result = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertEqual(result.subject_sha256, hashlib.sha256(legacy).hexdigest())
        self.assertEqual(result.entry_count, legacy.count(b"\n"))
        self.assertEqual(result.algorithm, "git-ls-tree-sha256-v1")

    def test_application_scope_matches_legacy_workflow_byte_for_byte(self) -> None:
        legacy = subprocess.check_output(
            ["git", "-C", str(self.repo), "ls-tree", "-r", "HEAD", "--", *APPLICATION_PATHS]
        )
        result = calculate_release_subject(scope="application", repo=self.repo)
        self.assertEqual(result.subject_sha256, hashlib.sha256(legacy).hexdigest())

    def test_subject_is_deterministic_for_same_commit(self) -> None:
        first = calculate_release_subject(scope="runtime", repo=self.repo)
        second = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertEqual(first.subject_sha256, second.subject_sha256)
        self.assertEqual(first.commit_sha, second.commit_sha)
        self.assertEqual(first.tree_sha, second.tree_sha)

    def test_untracked_and_uncommitted_changes_do_not_change_subject(self) -> None:
        before = calculate_release_subject(scope="runtime", repo=self.repo)
        (self.repo / "app/service.py").write_text("VALUE = 999\n", encoding="utf-8")
        (self.repo / "app/untracked.py").write_text("UNTRACKED = True\n", encoding="utf-8")
        after = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertEqual(before.subject_sha256, after.subject_sha256)

    def test_out_of_scope_commit_does_not_change_runtime_subject(self) -> None:
        before = calculate_release_subject(scope="runtime", repo=self.repo)
        (self.repo / "docs/new-note.md").write_text("not runtime\n", encoding="utf-8")
        self.commit_all("add documentation only")
        after = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertEqual(before.subject_sha256, after.subject_sha256)
        self.assertNotEqual(before.commit_sha, after.commit_sha)

    def test_runtime_file_change_changes_runtime_subject(self) -> None:
        before = calculate_release_subject(scope="runtime", repo=self.repo)
        (self.repo / "creator_app/api.py").write_text("API = False\n", encoding="utf-8")
        self.commit_all("change runtime file")
        after = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertNotEqual(before.subject_sha256, after.subject_sha256)

    def test_application_scope_includes_tests_and_scripts_but_not_app_root(self) -> None:
        before = calculate_release_subject(scope="application", repo=self.repo)
        (self.repo / "tests/test_new.py").write_text("def test_new(): pass\n", encoding="utf-8")
        self.commit_all("add application test")
        after_test = calculate_release_subject(scope="application", repo=self.repo)
        self.assertNotEqual(before.subject_sha256, after_test.subject_sha256)

        (self.repo / "app/other.py").write_text("OTHER = True\n", encoding="utf-8")
        self.commit_all("add app root file")
        after_app = calculate_release_subject(scope="application", repo=self.repo)
        self.assertEqual(after_test.subject_sha256, after_app.subject_sha256)

    def test_executable_mode_is_part_of_tree_subject(self) -> None:
        before = calculate_release_subject(scope="runtime", repo=self.repo)
        self.git("update-index", "--chmod=+x", "app/service.py")
        self.git("commit", "-qm", "change executable mode")
        after = calculate_release_subject(scope="runtime", repo=self.repo)
        self.assertNotEqual(before.subject_sha256, after.subject_sha256)

    def test_branch_and_commit_refs_resolve_to_same_subject(self) -> None:
        commit = self.git("rev-parse", "HEAD")
        by_branch = calculate_release_subject(ref="main", scope="runtime", repo=self.repo)
        by_sha = calculate_release_subject(ref=commit, scope="runtime", repo=self.repo)
        self.assertEqual(by_branch.subject_sha256, by_sha.subject_sha256)

    def test_calculates_subject_from_linked_git_worktree(self) -> None:
        expected = calculate_release_subject(scope="runtime", repo=self.repo).subject_sha256
        with tempfile.TemporaryDirectory() as parent:
            worktree = Path(parent) / "target"
            self.git("worktree", "add", "--detach", str(worktree), "HEAD")
            try:
                actual = calculate_release_subject(scope="runtime", repo=worktree).subject_sha256
            finally:
                self.git("worktree", "remove", "--force", str(worktree))
        self.assertEqual(actual, expected)

    def test_unknown_scope_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_release_subject(scope="everything", repo=self.repo)

    def test_unknown_ref_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            calculate_release_subject(ref="does-not-exist", repo=self.repo)

    def test_expected_subject_check_fails_closed(self) -> None:
        actual = calculate_release_subject(scope="runtime", repo=self.repo).subject_sha256
        matching = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--scope",
                "runtime",
                "--repo",
                str(self.repo),
                "--expected-subject",
                actual,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(matching.returncode, 0, matching.stderr)

        mismatch = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--scope",
                "runtime",
                "--repo",
                str(self.repo),
                "--expected-subject",
                "0" * 64,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(mismatch.returncode, 1)
        self.assertIn("release subject mismatch", mismatch.stderr)
        self.assertEqual(
            calculate_release_subject(scope="runtime", repo=self.repo).subject_sha256,
            actual,
        )

    def test_cli_json_contains_subject_provenance(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--scope",
                "runtime",
                "--ref",
                "HEAD",
                "--repo",
                str(self.repo),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scope"], "runtime")
        self.assertEqual(payload["commit_sha"], self.git("rev-parse", "HEAD"))
        self.assertEqual(
            payload["subject_sha256"],
            calculate_release_subject(repo=self.repo).subject_sha256,
        )
        self.assertEqual(len(payload["calculator_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
