from creator_app.ai_gateway.contracts import (
    AttestationState,
    ModelCapability,
    ModelDescriptor,
    ModelProvenance,
    ModelRiskClass,
)
from creator_app.ai_gateway.model_governance import (
    ModelUseLane,
    authorize_model_use,
    infer_effective_risk,
)


def _model(**overrides):
    values = {
        "provider_id": "example",
        "model_id": "example/model",
        "capabilities": frozenset({ModelCapability.TEXT}),
    }
    values.update(overrides)
    return ModelDescriptor(**values)


def test_safety_modified_name_is_auto_classified() -> None:
    model = _model(model_id="OBLITERATUS/Qwen3.8-27B-OBLITERATED")
    assert infer_effective_risk(model) is ModelRiskClass.SAFETY_MODIFIED


def test_safety_modified_model_is_denied_outside_red_team() -> None:
    model = _model(model_id="example/uncensored-model")
    decision = authorize_model_use(model, ModelUseLane.DEVELOPMENT)
    assert decision.allowed is False
    assert decision.quarantine_required is True
    assert decision.effective_risk is ModelRiskClass.SAFETY_MODIFIED


def test_safety_modified_model_is_allowed_only_in_red_team_lane() -> None:
    model = _model(model_id="example/abliterated-model")
    decision = authorize_model_use(model, ModelUseLane.RED_TEAM)
    assert decision.allowed is True
    assert decision.quarantine_required is True


def test_unverified_standard_model_is_denied_for_production() -> None:
    model = _model()
    decision = authorize_model_use(model, ModelUseLane.PRODUCTION)
    assert decision.allowed is False
    assert "verified model provenance" in decision.reason


def test_verified_model_requires_revision_and_weight_digest() -> None:
    model = _model(
        provenance=ModelProvenance(attestation=AttestationState.VERIFIED),
    )
    decision = authorize_model_use(model, ModelUseLane.PRODUCTION)
    assert decision.allowed is False
    assert "revision_sha and weight_digest" in decision.reason


def test_attested_standard_model_can_enter_production_lane() -> None:
    model = _model(
        provenance=ModelProvenance(
            model_repo="example/model",
            revision_sha="a" * 40,
            weight_digest="sha256:" + "b" * 64,
            attestation=AttestationState.VERIFIED,
        ),
    )
    decision = authorize_model_use(model, ModelUseLane.PRODUCTION)
    assert decision.allowed is True
    assert decision.quarantine_required is False


def test_frontier_capabilities_exist() -> None:
    expected = {
        ModelCapability.VIDEO,
        ModelCapability.LONG_CONTEXT,
        ModelCapability.THINKING_CONTROL,
        ModelCapability.THINKING_CONTINUITY,
        ModelCapability.AGENTIC_EXECUTION,
        ModelCapability.ENVIRONMENT_FEEDBACK,
        ModelCapability.LOCAL_MULTIMODAL,
        ModelCapability.QUANTIZED_RUNTIME,
        ModelCapability.RED_TEAM_MODEL,
        ModelCapability.MODEL_ATTESTATION,
    }
    assert len(expected) == 10
