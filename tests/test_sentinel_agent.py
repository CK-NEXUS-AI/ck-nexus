from creator_app.ai_team.agent_models import RequestPriority, TaskStatus, TeamRequest
from creator_app.ai_team.agents.sentinel import SentinelAgent


def _request() -> TeamRequest:
    return TeamRequest(
        request_id="sentinel-test",
        description="inspect evidence",
        priority=RequestPriority.NORMAL,
    )


def test_sentinel_rejects_non_string_evidence_fields() -> None:
    bundle = {
        "subject_sha": None,
        "source": None,
        "observed_at": None,
        "checks": [
            {
                "name": None,
                "status": None,
                "evidence_ref": None,
                "subject_sha": None,
                "artifact_sha256": None,
            }
        ],
    }

    result = SentinelAgent().process(_request(), context={"evidence_bundle": bundle})

    assert result.status is TaskStatus.BLOCKED
    assert result.metadata["evidence_status"] == "INCOMPLETE"
    assert "subject_sha (40/64 hex characters)" in result.warnings[-1]
    assert "source" in result.warnings[-1]
    assert "observed_at (ISO-8601 with timezone)" in result.warnings[-1]
    assert "checks[0].name" in result.warnings[-1]
    assert "checks[0].status" in result.warnings[-1]
    assert "checks[0].evidence_ref" in result.warnings[-1]
    assert "checks[0].subject_sha must match bundle subject" in result.warnings[-1]
    assert "checks[0].artifact_sha256" in result.warnings[-1]


def test_sentinel_accepts_only_string_values_for_check_fields() -> None:
    sha = "a" * 64
    bundle = {
        "subject_sha": sha,
        "source": "ci",
        "observed_at": "2026-11-05T10:00:00+07:00",
        "checks": [
            {
                "name": "unit-tests",
                "status": "PASS",
                "evidence_ref": "run://123",
                "subject_sha": sha,
                "artifact_sha256": None,
            }
        ],
    }

    result = SentinelAgent().process(_request(), context={"evidence_bundle": bundle})

    assert result.status is TaskStatus.BLOCKED
    assert result.metadata["evidence_status"] == "INCOMPLETE"
    assert "checks[0].artifact_sha256" in result.warnings[-1]
