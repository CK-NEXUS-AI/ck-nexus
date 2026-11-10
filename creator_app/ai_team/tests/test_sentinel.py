from __future__ import annotations

from creator_app.ai_team.agent_models import TaskStatus, TeamRequest
from creator_app.ai_team.agents.sentinel import SentinelAgent
from creator_app.ai_team.team_director import TeamDirector


class TestSentinelEvidenceGate:
    """Sentinel ต้อง fail-closed เมื่อไม่มีหลักฐานหรือไม่มี L3 attestation."""

    def test_evidence_request_without_bundle_is_blocked(self):
        team = TeamDirector()
        result = team.process_request("verify release evidence for main")

        assert result.status == TaskStatus.BLOCKED
        assert "Sentinel" in result.team_members_used
        assert "NO EVIDENCE" in result.final_output

    def test_candidate_bundle_still_requires_core_attestation(self):
        subject_sha = "a" * 40
        request = TeamRequest(request_id="sentinel-test", description="verify release")
        bundle = {
            "subject_sha": subject_sha,
            "source": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/123",
            "observed_at": "2026-11-05T03:00:00Z",
            "checks": [
                {
                    "name": "ci",
                    "status": "PASS",
                    "subject_sha": subject_sha,
                    "evidence_ref": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/123",
                    "artifact_sha256": "b" * 64,
                }
            ],
        }
        result = SentinelAgent().process(request, context={"evidence_bundle": bundle})

        assert result.status == TaskStatus.BLOCKED
        assert result.metadata["evidence_status"] == "CANDIDATE_UNVERIFIED"
        assert result.metadata["verification_scope"] == "STRUCTURE_ONLY"
        assert result.metadata["artifact_digest_verified"] is False
        assert result.metadata["authority_attestation_verified"] is False
        assert "Core/L3" in result.output

    def test_only_sentinel_receives_evidence_bundle(self, monkeypatch):
        team = TeamDirector()
        bundle = {"subject_sha": "a" * 40, "checks": []}
        received = {}

        for name, agent in team.agents.items():
            original = agent.process

            def capture(request, context=None, *, _name=name, _original=original):
                if context and "evidence_bundle" in context:
                    received[_name] = context["evidence_bundle"]
                return _original(request, context=context)

            monkeypatch.setattr(agent, "process", capture)

        team.process_request("verify release evidence", evidence_bundle=bundle)

        assert received == {"sentinel": bundle}

    def test_failed_evidence_check_fails_gate(self):
        subject_sha = "c" * 40
        request = TeamRequest(request_id="sentinel-fail", description="verify security release")
        bundle = {
            "subject_sha": subject_sha,
            "source": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/456",
            "observed_at": "2026-11-05T03:00:00+07:00",
            "checks": [
                {
                    "name": "security-scan",
                    "status": "FAIL",
                    "subject_sha": subject_sha,
                    "evidence_ref": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/456",
                    "artifact_sha256": "d" * 64,
                }
            ],
        }
        result = SentinelAgent().process(request, context={"evidence_bundle": bundle})

        assert result.status == TaskStatus.FAILED
        assert result.metadata["evidence_status"] == "FAILED_CHECKS"
        assert "security-scan" in result.output
