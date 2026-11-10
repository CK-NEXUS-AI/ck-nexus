from datetime import date

import pytest

from scripts.q16_risk_approval import (
    MARKER,
    MEDIUM_MARKER,
    verify_independent_medium_review,
    verify_owner_risk_approval,
)

BASE_IMAGE = (
    "python:3.12.16-slim-trixie@sha256:"
    "e695ab189fa2d082b1c61c69a6b888a5adeca61ceeccad107b1ed2a125721a9e"
)
VULNERABILITY_IDS = {"CVE-2025-0001", "CVE-2026-0002"}
FINDING_REFS = {
    "CVE-2025-0001|libfoo|1.0",
    "CVE-2026-0002|libbar|2.0",
}


def _comment(**overrides):
    item = {
        "user": {"login": "spinlnw10-art", "type": "User"},
        "author_association": "MEMBER",
        "created_at": "2026-11-05T14:00:00Z",
        "html_url": "https://github.com/CK-NEXUS-AI/ck-nexus/pull/354#issuecomment-123",
        "body": "\n".join(
            [
                MARKER,
                "source_sha: " + "a" * 40,
                "base_image: " + BASE_IMAGE,
                "image_config_digest: sha256:" + "b" * 64,
                "report_sha256: " + "c" * 64,
                "vulnerability_ids: CVE-2025-0001,CVE-2026-0002",
                "finding_refs: CVE-2025-0001|libfoo|1.0;CVE-2026-0002|libbar|2.0",
                "expires_at: 2026-12-05",
                "rationale: reviewed package reachability and compensating controls",
            ]
        ),
    }
    item.update(overrides)
    return item


def _verify(comments):
    return verify_owner_risk_approval(
        comments,
        source_sha="a" * 40,
        base_image=BASE_IMAGE,
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids=VULNERABILITY_IDS,
        finding_refs=FINDING_REFS,
        today=date(2026, 11, 10),
    )


def _medium_comment(**overrides):
    comment = _comment(**overrides)
    comment["user"] = {"login": "independent-reviewer", "type": "User"}
    comment["author_association"] = "COLLABORATOR"
    comment["body"] = comment["body"].replace(MARKER, MEDIUM_MARKER)
    return comment


def _verify_medium(comments):
    return verify_independent_medium_review(
        comments,
        source_sha="a" * 40,
        base_image=BASE_IMAGE,
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids=VULNERABILITY_IDS,
        finding_refs=FINDING_REFS,
        today=date(2026, 11, 10),
    )


def test_accepts_authenticated_owner_attestation_bound_to_exact_candidate_image_and_findings():
    assert _verify([_comment()])["actor"] == "spinlnw10-art"


def test_rejects_non_owner_and_bot_comments():
    assert _verify([_comment(user={"login": "someone-else", "type": "User"})]) is None
    assert _verify([_comment(user={"login": "spinlnw10-art", "type": "Bot"})]) is None


def test_rejects_mismatched_candidate_image_report_base_or_vulnerability_set():
    for old, new in [
        ("source_sha: " + "a" * 40, "source_sha: " + "d" * 40),
        ("base_image: " + BASE_IMAGE, "base_image: python:3.12-slim"),
        (
            "image_config_digest: sha256:" + "b" * 64,
            "image_config_digest: sha256:" + "e" * 64,
        ),
        ("report_sha256: " + "c" * 64, "report_sha256: " + "f" * 64),
        (
            "vulnerability_ids: CVE-2025-0001,CVE-2026-0002",
            "vulnerability_ids: CVE-2025-0001",
        ),
    ]:
        comment = _comment(body=_comment()["body"].replace(old, new))
        assert _verify([comment]) is None


def test_rejects_expired_or_overlong_approval():
    expired = _comment(body=_comment()["body"].replace("2026-12-05", "2026-11-06"))
    overlong = _comment(body=_comment()["body"].replace("2026-12-05", "2027-01-01"))
    assert _verify([expired]) is None
    assert _verify([overlong]) is None


def test_rejects_duplicate_or_missing_attestation_fields():
    body = _comment()["body"] + "\nsource_sha: " + "a" * 40
    assert _verify([_comment(body=body)]) is None
    assert _verify([_comment(body=MARKER)]) is None


@pytest.mark.parametrize("mutator", ["missing", "extra", "altered"])
@pytest.mark.parametrize("review_kind", ["owner", "medium"])
def test_both_attestations_require_exact_nonempty_package_finding_refs(mutator, review_kind):
    comment = _comment() if review_kind == "owner" else _medium_comment()
    lines = comment["body"].splitlines()
    if mutator == "missing":
        lines = [line for line in lines if not line.startswith("finding_refs:")]
    elif mutator == "extra":
        lines = [
            line + ";CVE-2026-9999|libbaz|3.0" if line.startswith("finding_refs:") else line
            for line in lines
        ]
    else:
        lines = [
            line.replace("libfoo", "libqux") if line.startswith("finding_refs:") else line
            for line in lines
        ]
    comment["body"] = "\n".join(lines)
    verifier = _verify if review_kind == "owner" else _verify_medium
    assert verifier([comment]) is None


def test_both_attestations_reject_mismatched_base_image():
    owner = _comment(body=_comment()["body"].replace(BASE_IMAGE, "python:3.12-slim"))
    medium = _medium_comment(body=_medium_comment()["body"].replace(BASE_IMAGE, "python:3.12-slim"))
    assert _verify([owner]) is None
    assert _verify_medium([medium]) is None


def test_medium_review_requires_non_owner_collaborator_and_exact_findings():
    approved = _verify_medium([_medium_comment()])
    assert approved and approved["actor"] == "independent-reviewer"


def test_medium_review_rejects_owner_and_non_collaborator():
    comment = _comment()
    comment["body"] = comment["body"].replace(MARKER, MEDIUM_MARKER)
    assert _verify_medium([comment]) is None
    outsider = _medium_comment()
    outsider["user"] = {"login": "outsider", "type": "User"}
    outsider["author_association"] = "NONE"
    assert _verify_medium([outsider]) is None
