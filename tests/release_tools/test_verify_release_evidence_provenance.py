from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).parents[2]
    / ".github/release-tools/verify_release_evidence_provenance.py"
)
SPEC = importlib.util.spec_from_file_location("release_evidence_verifier", MODULE_PATH)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

REPOSITORY = "spinlnw10-art/ck-nexus"
SOURCE_SHA = "a" * 40
SOURCE_TREE = "b" * 40
RUN_SHA = SOURCE_SHA
EXPECTED_SUBJECT = "c" * 64


def _evidence(
    tmp_path: Path,
    *,
    source_sha: object = SOURCE_SHA,
    source_tree: object = SOURCE_TREE,
) -> Path:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "Q13_POSTGRES_DR.json").write_text(
        json.dumps({
            "gate": "Q13",
            "release_subject_manifest_sha256": EXPECTED_SUBJECT,
            "artifact_id": 123,
            "artifact_digest": "sha256:abc123",
            "github_run_id": 456,
            "source_sha": source_sha,
            "source_tree": source_tree,
            "result": "PASS_CANDIDATE",
        }), encoding="utf-8"
    )
    return evidence_dir


def _api_responses(
    *,
    run_sha: str = RUN_SHA,
    artifact_sha: str = RUN_SHA,
    tree_sha: str = SOURCE_TREE,
):
    return [
        {"expired": False, "digest": "sha256:abc123", "workflow_run": {
            "id": 456, "head_branch": "release/q10-q16-closure", "head_sha": artifact_sha}},
        {"repository": {"full_name": REPOSITORY}, "head_sha": run_sha,
         "head_branch": "release/q10-q16-closure", "conclusion": "success", "name": "Q13 gate"},
        {"commit": {"tree": {"sha": tree_sha}}},
    ]


class ProvenanceVerifierTests(unittest.TestCase):
    def verify_case(
        self,
        *,
        run_sha=RUN_SHA,
        artifact_sha=RUN_SHA,
        tree_sha=SOURCE_TREE,
        source_sha=SOURCE_SHA,
        source_tree=SOURCE_TREE,
    ):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(verifier, "EVIDENCE_FILES", ("Q13_POSTGRES_DR.json",)),
            patch.object(
                verifier,
                "_api_json",
                side_effect=_api_responses(
                    run_sha=run_sha, artifact_sha=artifact_sha, tree_sha=tree_sha
                ),
            ),
        ):
            return verifier.verify(
                repository=REPOSITORY,
                token="test-token-not-a-real-secret",
                expected_subject=EXPECTED_SUBJECT,
                evidence_dir=_evidence(
                    Path(tmp), source_sha=source_sha, source_tree=source_tree
                ),
            )

    def test_matching_run_commit_and_tree_pass(self):
        report = self.verify_case()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(SOURCE_SHA, RUN_SHA)
        self.assertTrue(report["evidence"][0]["checks"]["run_head_sha_matches_evidence"])
        self.assertTrue(report["evidence"][0]["checks"]["artifact_head_sha_matches_run"])
        self.assertTrue(report["evidence"][0]["checks"]["source_tree_matches_github_commit"])

    def test_malformed_source_sha_fails_closed_before_api_lookup(self):
        report = self.verify_case(source_sha="z" * 40)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any("source_sha missing or invalid" in item for item in report["provenance_failures"])
        )

    def test_missing_source_tree_fails_closed_before_api_lookup(self):
        report = self.verify_case(source_tree=None)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any("source_tree missing or invalid" in item for item in report["provenance_failures"])
        )

    def test_workflow_head_sha_must_match_evidence_source_sha(self):
        report = self.verify_case(run_sha="d" * 40, artifact_sha="d" * 40)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any(
                "run_head_sha_matches_evidence" in item
                for item in report["provenance_failures"]
            )
        )

    def test_artifact_head_sha_must_match_workflow_run(self):
        report = self.verify_case(artifact_sha="e" * 40)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any(
                "artifact_head_sha_matches_run" in item
                for item in report["provenance_failures"]
            )
        )

    def test_run_branch_must_match_artifact_branch(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(verifier, "EVIDENCE_FILES", ("Q13_POSTGRES_DR.json",)),
            patch.object(
                verifier,
                "_api_json",
                side_effect=[
                    {"expired": False, "digest": "sha256:abc123", "workflow_run": {
                        "id": 456, "head_branch": "release/q10-q16-closure", "head_sha": RUN_SHA}},
                    {
                        "repository": {"full_name": REPOSITORY},
                        "head_sha": RUN_SHA,
                        "head_branch": "different-branch",
                        "conclusion": "success",
                        "name": "Q13 gate",
                    },
                    {"commit": {"tree": {"sha": SOURCE_TREE}}},
                ],
            ),
        ):
            report = verifier.verify(
                repository=REPOSITORY,
                token="test-token-not-a-real-secret",
                expected_subject=EXPECTED_SUBJECT,
                evidence_dir=_evidence(Path(tmp)),
            )
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any("run_branch_matches_artifact" in item for item in report["provenance_failures"])
        )

    def test_mismatched_commit_tree_fails_closed(self):
        report = self.verify_case(tree_sha="f" * 40)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(
            any(
                "source_tree_matches_github_commit" in item
                for item in report["provenance_failures"]
            )
        )


if __name__ == "__main__":
    unittest.main()
