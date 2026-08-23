from creator_app.integrations.mcp_admission import (
    AdmissionStage,
    CandidateClass,
    MCPAdmissionController,
    MCPServerCandidate,
)


def _candidate(**overrides):
    values = dict(
        name="io.github.example/server",
        version="1.0.0",
        publisher_namespace="io.github.example",
        source_repository="https://github.com/example/server",
        package_type="pypi",
        package_identifier="example-mcp",
        license_id="Apache-2.0",
        publisher_identity_verified=True,
        source_provenance_verified=True,
        license_verified=True,
        cost_known_free=True,
        cost_known_paid=False,
        privacy_reviewed=True,
        data_leaves_ck_boundary=False,
        requests_write_capability=False,
        requests_credentials=False,
    )
    values.update(overrides)
    return MCPServerCandidate(**values)


def test_safe_candidate_stops_in_quarantine_until_sandbox_verification() -> None:
    result = MCPAdmissionController().assess(_candidate())
    assert result.stage is AdmissionStage.QUARANTINED
    assert result.classification is CandidateClass.LOCAL_EVALUATE
    assert result.activation_allowed is False
    assert result.reasons == ("sandbox_verification_required_before_activation",)


def test_auto_install_is_rejected() -> None:
    result = MCPAdmissionController().assess(_candidate(auto_install_requested=True))
    assert result.stage is AdmissionStage.REJECTED
    assert result.classification is CandidateClass.REJECT
    assert result.activation_allowed is False


def test_unknown_cost_never_activates() -> None:
    result = MCPAdmissionController().assess(_candidate(cost_known_free=False))
    assert result.classification is CandidateClass.PAID_OR_UNKNOWN_COST
    assert result.activation_allowed is False


def test_external_data_write_and_credentials_require_approval() -> None:
    result = MCPAdmissionController().assess(
        _candidate(
            data_leaves_ck_boundary=True,
            requests_write_capability=True,
            requests_credentials=True,
        )
    )
    assert result.stage is AdmissionStage.QUARANTINED
    assert result.classification is CandidateClass.APPROVAL_REQUIRED
    assert "external_data_transfer_requires_approval" in result.reasons
    assert "write_capability_requires_approval" in result.reasons
    assert "credential_scope_requires_broker_review" in result.reasons


def test_admission_cannot_skip_stages() -> None:
    assert MCPAdmissionController.can_advance(
        AdmissionStage.QUARANTINED, AdmissionStage.SANDBOX_TESTED
    )
    assert not MCPAdmissionController.can_advance(
        AdmissionStage.QUARANTINED, AdmissionStage.CONNECTED
    )


def test_candidate_digest_is_deterministic_and_bound_to_metadata() -> None:
    controller = MCPAdmissionController()
    first = controller.assess(_candidate())
    second = controller.assess(_candidate())
    changed = controller.assess(_candidate(version="1.0.1"))
    assert first.candidate_digest == second.candidate_digest
    assert first.candidate_digest != changed.candidate_digest
