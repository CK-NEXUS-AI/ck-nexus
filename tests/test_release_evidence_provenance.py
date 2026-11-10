from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "release-tools"
    / "verify_release_evidence_provenance.py"
)
SPEC = importlib.util.spec_from_file_location("release_evidence_provenance", MODULE_PATH)
assert SPEC and SPEC.loader
provenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provenance)


def _page(*, review_cursor=None, comment_cursor=None, second=False):
    review_nodes = (
        [
            {
                "state": "APPROVED",
                "commit": {"oid": "a" * 40},
                "body": "CKNEXUS-Q10-REVIEW-APPROVED",
                "submittedAt": "2026-11-05T12:00:00Z",
                "url": "https://github.com/CK-NEXUS-AI/ck-nexus/pull/354#pullrequestreview-1",
                "authorAssociation": "COLLABORATOR",
                "author": {"login": "reviewer", "__typename": "User"},
            }
        ]
        if not second
        else [
            {
                "state": "COMMENTED",
                "commit": {"oid": "b" * 40},
                "body": "later comment",
                "submittedAt": "2026-11-05T12:01:00Z",
                "url": "https://github.com/CK-NEXUS-AI/ck-nexus/pull/354#pullrequestreview-2",
                "authorAssociation": "COLLABORATOR",
                "author": {"login": "reviewer", "__typename": "User"},
            }
        ]
    )
    comment_nodes = (
        [
            {
                "body": "CKNEXUS-Q10-OWNER-APPROVED",
                "createdAt": "2026-11-05T12:02:00Z",
                "url": "https://github.com/CK-NEXUS-AI/ck-nexus/pull/354#issuecomment-1",
                "authorAssociation": "OWNER",
                "author": {"login": "spinlnw10-art", "__typename": "User"},
            }
        ]
        if not second
        else []
    )
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviews": {
                        "nodes": review_nodes,
                        "pageInfo": {
                            "hasNextPage": not second,
                            "endCursor": "review-next" if not second else None,
                        },
                    },
                    "comments": {
                        "nodes": comment_nodes,
                        "pageInfo": {
                            "hasNextPage": not second,
                            "endCursor": "comment-next" if not second else None,
                        },
                    },
                }
            }
        }
    }


def test_pr_attestation_lookup_uses_graphql_post_and_paginates_both_connections(monkeypatch):
    calls = []
    responses = [_page(), _page(second=True)]

    def fake_api_payload(url, token, *, method="GET", body=None):
        calls.append((url, token, method, json.loads(body)))
        return responses.pop(0)

    monkeypatch.setattr(provenance, "_api_payload", fake_api_payload)
    reviews, comments = provenance._github_pr_attestations("CK-NEXUS-AI/ck-nexus", 354, "token")

    assert len(calls) == 2
    assert all(call[0] == "https://api.github.com/graphql" for call in calls)
    assert all(call[1] == "token" and call[2] == "POST" for call in calls)
    assert calls[1][3]["variables"]["reviewsCursor"] == "review-next"
    assert calls[1][3]["variables"]["commentsCursor"] == "comment-next"
    assert len(reviews) == 2
    assert reviews[0]["commit_id"] == "a" * 40
    assert reviews[0]["user"] == {"login": "reviewer", "type": "User"}
    assert len(comments) == 1
    assert comments[0]["author_association"] == "OWNER"


def test_evidence_filename_gate_mapping_is_fixed_and_not_self_asserted():
    assert provenance.EXPECTED_GATES_BY_FILENAME == {
        "Q10_DEPENDENCY_AUDIT.json": "Q10",
        "Q11_OPENAI_LIVE.json": "Q11",
        "Q12_CGROUP_V2.json": "Q12",
        "Q13_POSTGRES_DR.json": "Q13",
        "Q14_OBSERVABILITY_ALERT.json": "Q14",
        "Q15_CLEAN_MACHINE.json": "Q15",
        "Q16_PRODUCTION_IMAGE.json": "Q16_PRODUCTION_IMAGE",
        "Q16_RUNTIME_LICENSE_SUMMARY.json": "Q16_RUNTIME_LICENSES",
    }


def test_q10_review_requires_substantive_assessment_fields():
    marker_only = "\n".join(
        [
            "CKNEXUS-Q10-REVIEW-APPROVED",
            "COVERAGE-REVIEWED",
            "FINDINGS-REVIEWED",
            "NON-EQUIVALENCE-ACKNOWLEDGED",
        ]
    )
    assert not provenance._review_body_has_substance(marker_only)

    substantive = "\n".join(
        [
            "scanner_configuration_review: Reviewed pinned versions, ruleset identity, and scope.",
            "findings_review: Reviewed all high-risk findings and documented their disposition.",
            "false_positive_handling_review: Reproduced each proposed false-positive exclusion.",
            "unresolved_risks: Remaining medium findings and non-Codex limits are documented.",
            "non_equivalence_assessment: Non-Codex tools are not equivalent to Codex Security.",
        ]
    )
    assert provenance._review_body_has_substance(substantive)
