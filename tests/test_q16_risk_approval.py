from datetime import date

from scripts.q16_risk_approval import MARKER, verify_owner_risk_approval


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
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids={"CVE-2025-0001", "CVE-2026-0002"},
        finding_refs={"CVE-2025-0001|libfoo|1.0", "CVE-2026-0002|libbar|2.0"},
        today=date(2026, 11, 10),
    )


def test_accepts_authenticated_owner_attestation_bound_to_exact_candidate_image_and_findings():
    assert _verify([_comment()])["actor"] == "spinlnw10-art"


def test_rejects_non_owner_and_bot_comments():
    assert _verify([_comment(user={"login": "someone-else", "type": "User"})]) is None
    assert _verify([_comment(user={"login": "spinlnw10-art", "type": "Bot"})]) is None


def test_rejects_mismatched_candidate_image_report_or_vulnerability_set():
    for old, new in [
        ("source_sha: " + "a" * 40, "source_sha: " + "d" * 40),
        ("image_config_digest: sha256:" + "b" * 64, "image_config_digest: sha256:" + "e" * 64),
        ("report_sha256: " + "c" * 64, "report_sha256: " + "f" * 64),
        ("vulnerability_ids: CVE-2025-0001,CVE-2026-0002", "vulnerability_ids: CVE-2025-0001"),
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


def test_medium_review_requires_non_owner_collaborator_and_exact_findings():
    from scripts.q16_risk_approval import verify_independent_medium_review

    comment = _comment()
    comment["user"] = {"login": "independent-reviewer", "type": "User"}
    comment["author_association"] = "COLLABORATOR"
    comment["body"] = comment["body"].replace(
        MARKER, "CKNEXUS-Q16-MEDIUM-REVIEW-APPROVED"
    )
    approved = verify_independent_medium_review(
        [comment],
        source_sha="a" * 40,
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids={"CVE-2025-0001", "CVE-2026-0002"},
        finding_refs={"CVE-2025-0001|libfoo|1.0", "CVE-2026-0002|libbar|2.0"},
        today=date(2026, 11, 10),
    )
    assert approved and approved["actor"] == "independent-reviewer"


def test_medium_review_rejects_owner_and_non_collaborator():
    from scripts.q16_risk_approval import verify_independent_medium_review

    comment = _comment()
    comment["body"] = comment["body"].replace(
        MARKER, "CKNEXUS-Q16-MEDIUM-REVIEW-APPROVED"
    )
    assert verify_independent_medium_review(
        [comment],
        source_sha="a" * 40,
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids={"CVE-2025-0001", "CVE-2026-0002"},
        finding_refs={"CVE-2025-0001|libfoo|1.0", "CVE-2026-0002|libbar|2.0"},
        today=date(2026, 11, 10),
    ) is None
    comment["user"] = {"login": "outsider", "type": "User"}
    comment["author_association"] = "NONE"
    assert verify_independent_medium_review(
        [comment],
        source_sha="a" * 40,
        image_config_digest="sha256:" + "b" * 64,
        report_sha256="c" * 64,
        vulnerability_ids={"CVE-2025-0001", "CVE-2026-0002"},
        finding_refs={"CVE-2025-0001|libfoo|1.0", "CVE-2026-0002|libbar|2.0"},
        today=date(2026, 11, 10),
    ) is None
