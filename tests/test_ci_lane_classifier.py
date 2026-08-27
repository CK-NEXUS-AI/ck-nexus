from __future__ import annotations

import pytest

from scripts.classify_ci_lane import CiLane, classify_ci_lane


@pytest.mark.parametrize(
    ("head_ref", "base_ref"),
    [
        ("post-p0/durable-execution-reconcile-v3", "main"),
        ("feat/agnes-expert-fabric-v1", "main"),
        ("research/universal-ai-os-capability-map-20260827", "main"),
        ("docs/gen7-capability-gap-matrix-v1", "main"),
        ("fix/agnes-triad-revision-lineage-v1", "post-p0/agnes-triad-debate-schema-v1"),
    ],
)
def test_development_prs_are_classified_without_release_evidence(
    head_ref: str,
    base_ref: str,
) -> None:
    assert (
        classify_ci_lane(
            event_name="pull_request",
            head_ref=head_ref,
            base_ref=base_ref,
        )
        is CiLane.DEVELOPMENT
    )


@pytest.mark.parametrize(
    ("head_ref", "base_ref"),
    [
        ("release/q10-q16-closure", "main"),
        ("prep/q10-native-deep-scan-contract-v2", "release/q10-q16-closure"),
        ("verify/q12-final-subject", "release/q10-q16-closure"),
        ("fix/q03-dependency-closure", "main"),
    ],
)
def test_release_bound_prs_keep_exact_evidence_semantics(
    head_ref: str,
    base_ref: str,
) -> None:
    assert (
        classify_ci_lane(
            event_name="pull_request",
            head_ref=head_ref,
            base_ref=base_ref,
        )
        is CiLane.RELEASE_EVIDENCE
    )


def test_unknown_pr_fails_closed_instead_of_guessing_release() -> None:
    assert (
        classify_ci_lane(
            event_name="pull_request",
            head_ref="mystery/change",
            base_ref="main",
        )
        is CiLane.BLOCKED_UNKNOWN
    )


def test_main_push_remains_release_evidence_bound() -> None:
    assert (
        classify_ci_lane(event_name="push", ref_name="main")
        is CiLane.RELEASE_EVIDENCE
    )


def test_release_push_remains_release_evidence_bound() -> None:
    assert (
        classify_ci_lane(event_name="push", ref_name="release/q04-q08-clean")
        is CiLane.RELEASE_EVIDENCE
    )


def test_manual_development_ref_stays_development() -> None:
    assert (
        classify_ci_lane(
            event_name="workflow_dispatch",
            ref_name="post-p0/ci-lane-classifier-v2",
        )
        is CiLane.DEVELOPMENT
    )


def test_unexpected_non_pr_ref_fails_closed() -> None:
    assert (
        classify_ci_lane(event_name="workflow_dispatch", ref_name="random-branch")
        is CiLane.BLOCKED_UNKNOWN
    )
