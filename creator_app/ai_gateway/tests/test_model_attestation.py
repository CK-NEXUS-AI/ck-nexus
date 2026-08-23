from creator_app.ai_gateway import (
    AttestationState,
    CapabilityCheck,
    ModelCapability,
    ModelDescriptor,
    ModelProvenance,
    attest_capabilities,
    behavioral_fingerprint,
)


def _model() -> ModelDescriptor:
    return ModelDescriptor(
        "provider",
        "model",
        frozenset({ModelCapability.TEXT, ModelCapability.REASONING}),
        runtime_id="runtime-a",
        provenance=ModelProvenance(
            revision_sha="abc123",
            weight_digest="sha256:deadbeef",
            quantization="bf16",
        ),
    )


def test_attestation_is_claimed_without_passing_checks() -> None:
    result = attest_capabilities(_model(), ())
    assert result.state is AttestationState.CLAIMED
    assert result.measured_capabilities == frozenset()
    assert len(result.digest) == 64


def test_attestation_is_measured_when_partial() -> None:
    result = attest_capabilities(
        _model(),
        (CapabilityCheck(ModelCapability.TEXT, True, "evd-text"),),
    )
    assert result.state is AttestationState.MEASURED
    assert result.measured_capabilities == frozenset({ModelCapability.TEXT})


def test_attestation_is_verified_only_when_all_claims_have_evidence() -> None:
    result = attest_capabilities(
        _model(),
        (
            CapabilityCheck(ModelCapability.TEXT, True, "evd-text"),
            CapabilityCheck(ModelCapability.REASONING, True, "evd-reasoning"),
        ),
    )
    assert result.state is AttestationState.VERIFIED
    assert result.evidence_ids == ("evd-reasoning", "evd-text")


def test_missing_evidence_prevents_verified_state() -> None:
    result = attest_capabilities(
        _model(),
        (
            CapabilityCheck(ModelCapability.TEXT, True, "evd-text"),
            CapabilityCheck(ModelCapability.REASONING, True, ""),
        ),
    )
    assert result.state is AttestationState.MEASURED


def test_behavioral_fingerprint_is_deterministic_and_identity_bound() -> None:
    model = _model()
    metrics = {"refusal_rate": 0.1, "tool_accuracy": 0.9}
    first = behavioral_fingerprint(model, metrics)
    second = behavioral_fingerprint(model, dict(reversed(list(metrics.items()))))
    assert first == second
    assert len(first) == 64

    changed = ModelDescriptor(
        model.provider_id,
        model.model_id,
        model.capabilities,
        runtime_id=model.runtime_id,
        provenance=ModelProvenance(
            revision_sha="different",
            weight_digest=model.provenance.weight_digest,
            quantization=model.provenance.quantization,
        ),
    )
    assert behavioral_fingerprint(changed, metrics) != first
