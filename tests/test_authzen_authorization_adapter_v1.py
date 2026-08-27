import pytest

from creator_app.agnes.cognitive import (
    AUTHZEN_ACCESS_EVALUATION_PATH,
    AUTHZEN_SPEC_VERSION,
    ActionProposal,
    AuthZENAdapter,
    GovernorDecision,
    RiskLevel,
)


def _request() -> dict:
    return {
        "subject": {"type": "agent", "id": "agnes"},
        "action": {"name": "read"},
        "resource": {"type": "document", "id": "evidence-1"},
        "context": {"channel": "shadow"},
    }


def _proposal(**overrides) -> ActionProposal:
    values = {
        "action": "read",
        "actor": "agnes",
        "scope": "document:evidence-1",
        "risk": RiskLevel.LOW,
    }
    values.update(overrides)
    return ActionProposal(**values)


def test_authzen_constants_bind_final_1_0_access_evaluation_contract() -> None:
    assert AUTHZEN_SPEC_VERSION == "1.0"
    assert AUTHZEN_ACCESS_EVALUATION_PATH == "/access/v1/evaluation"


def test_pdp_allow_still_requires_ck_governor_allow() -> None:
    result = AuthZENAdapter().enforce(_request(), {"decision": True}, _proposal())
    assert result.pdp_decision is True
    assert result.governor_result.decision is GovernorDecision.ALLOW
    assert result.allowed is True
    assert result.authority == "CK-NEXUS"
    assert len(result.evidence_digest) == 64


def test_pdp_deny_is_fail_closed_veto() -> None:
    result = AuthZENAdapter().enforce(_request(), {"decision": False}, _proposal())
    assert result.governor_result.decision is GovernorDecision.ALLOW
    assert result.allowed is False
    assert result.reason == "external_pdp_denied"


def test_pdp_allow_cannot_bypass_production_mutation_denial() -> None:
    request = _request()
    request["action"] = {"name": "deploy"}
    request["resource"] = {"type": "environment", "id": "production"}
    proposal = ActionProposal(
        action="deploy",
        actor="agnes",
        scope="environment:production",
        risk=RiskLevel.CRITICAL,
        production_mutation=True,
        verified=True,
        human_approved=True,
        evidence_refs=("evd-1",),
    )
    result = AuthZENAdapter().enforce(request, {"decision": True}, proposal)
    assert result.governor_result.decision is GovernorDecision.DENY
    assert result.allowed is False
    assert result.reason == "ck_governor_denied"


def test_pdp_context_cannot_self_grant_ck_approval_or_verification() -> None:
    response = {
        "decision": True,
        "context": {
            "human_approved": True,
            "verified": True,
            "production_authorized": True,
        },
    }
    proposal = _proposal(
        risk=RiskLevel.HIGH,
        external_write=True,
        human_approved=False,
        verified=False,
        evidence_refs=(),
    )
    result = AuthZENAdapter().enforce(_request(), response, proposal)
    assert result.governor_result.decision is GovernorDecision.REQUIRE_APPROVAL
    assert result.allowed is False
    assert result.reason == "ck_governor_requires_approval"


def test_authzen_request_must_bind_exact_ck_actor_action_and_scope() -> None:
    adapter = AuthZENAdapter()
    with pytest.raises(ValueError, match="subject is not bound"):
        adapter.enforce(_request(), {"decision": True}, _proposal(actor="other-agent"))
    with pytest.raises(ValueError, match="action is not bound"):
        adapter.enforce(_request(), {"decision": True}, _proposal(action="write"))
    with pytest.raises(ValueError, match="resource is not bound"):
        adapter.enforce(_request(), {"decision": True}, _proposal(scope="document:other"))


def test_authzen_response_decision_must_be_boolean() -> None:
    with pytest.raises(ValueError, match="decision must be boolean"):
        AuthZENAdapter().enforce(_request(), {"decision": 1}, _proposal())


def test_authzen_rejects_hidden_top_level_authority_channels() -> None:
    request = _request()
    request["production_authorized"] = True
    with pytest.raises(ValueError, match="unsupported AuthZEN request keys"):
        AuthZENAdapter().enforce(request, {"decision": True}, _proposal())

    with pytest.raises(ValueError, match="unsupported AuthZEN response keys"):
        AuthZENAdapter().enforce(
            _request(),
            {"decision": True, "ck_verified": True},
            _proposal(),
        )


def test_authzen_requires_final_1_0_entity_shapes() -> None:
    request = _request()
    request["subject"] = {"type": "agent"}
    with pytest.raises(ValueError, match="subject.id"):
        AuthZENAdapter().enforce(request, {"decision": True}, _proposal())

    request = _request()
    request["action"] = {"name": ""}
    with pytest.raises(ValueError, match="action.name"):
        AuthZENAdapter().enforce(request, {"decision": True}, _proposal())


def test_authzen_digest_is_deterministic_and_decision_bound() -> None:
    adapter = AuthZENAdapter()
    first = adapter.enforce(_request(), {"decision": True}, _proposal())
    second = adapter.enforce(_request(), {"decision": True}, _proposal())
    denied = adapter.enforce(_request(), {"decision": False}, _proposal())
    assert first.evidence_digest == second.evidence_digest
    assert first.evidence_digest != denied.evidence_digest
