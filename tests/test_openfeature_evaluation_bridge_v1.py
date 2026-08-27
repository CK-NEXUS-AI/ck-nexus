from creator_app.feature_flags import (
    OPENFEATURE_SPEC_VERSION,
    NoOpProvider,
    OpenFeatureEvaluationBridge,
    ProviderMetadata,
    ResolutionDetails,
)


class WorkingProvider:
    metadata = ProviderMetadata("test-provider")

    def resolve_boolean_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails(True, reason="TARGETING_MATCH", variant="on")

    def resolve_string_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails("candidate", reason="STATIC")

    def resolve_number_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails(25, reason="STATIC")

    def resolve_object_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails({"mode": "shadow"}, reason="STATIC")


class FailingProvider(WorkingProvider):
    metadata = ProviderMetadata("failing-provider")

    def resolve_boolean_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        raise RuntimeError("provider unavailable")


class WrongTypeProvider(WorkingProvider):
    metadata = ProviderMetadata("wrong-type-provider")

    def resolve_boolean_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails("yes", reason="STATIC")


class ErrorDetailsProvider(WorkingProvider):
    metadata = ProviderMetadata("error-details-provider")

    def resolve_boolean_value(self, flag_key, default_value, context):
        del flag_key, default_value, context
        return ResolutionDetails(
            True,
            reason="ERROR",
            error_code="PROVIDER_NOT_READY",
            error_message="not ready",
        )


def test_openfeature_spec_version_is_current_v090() -> None:
    assert OPENFEATURE_SPEC_VERSION == "0.9.0"


def test_noop_provider_returns_supplied_default() -> None:
    bridge = OpenFeatureEvaluationBridge(NoOpProvider())
    details = bridge.get_boolean_details("feature-x", False, {"targetingKey": "user-1"})
    assert details.value is False
    assert details.default_used is True
    assert details.provider_name == "ck-nexus-no-op"
    assert details.error_code is None


def test_typed_provider_resolution_is_preserved() -> None:
    bridge = OpenFeatureEvaluationBridge(WorkingProvider())
    assert bridge.get_boolean_value("flag-bool", False) is True
    assert bridge.get_string_value("flag-string", "default") == "candidate"
    assert bridge.get_number_value("flag-number", 0) == 25
    assert bridge.get_object_value("flag-object", {}) == {"mode": "shadow"}


def test_provider_exception_returns_default_without_escaping() -> None:
    details = OpenFeatureEvaluationBridge(FailingProvider()).get_boolean_details(
        "feature-x",
        False,
    )
    assert details.value is False
    assert details.default_used is True
    assert details.reason == "ERROR"
    assert details.error_code == "GENERAL"


def test_provider_error_details_return_default() -> None:
    details = OpenFeatureEvaluationBridge(ErrorDetailsProvider()).get_boolean_details(
        "feature-x",
        False,
    )
    assert details.value is False
    assert details.default_used is True
    assert details.error_code == "PROVIDER_NOT_READY"


def test_type_mismatch_returns_default() -> None:
    details = OpenFeatureEvaluationBridge(WrongTypeProvider()).get_boolean_details(
        "feature-x",
        False,
    )
    assert details.value is False
    assert details.default_used is True
    assert details.error_code == "TYPE_MISMATCH"


def test_flag_result_never_grants_ck_authority() -> None:
    bridge = OpenFeatureEvaluationBridge(WorkingProvider())
    details = bridge.get_boolean_details("production_mutation", False)
    assert details.value is True
    assert details.authority == "CK-NEXUS"
    assert details.permission_granted is False
    assert details.verification_upgrade_allowed is False
    assert details.production_mutation_allowed is False


def test_evidence_digest_is_deterministic_and_context_bound() -> None:
    bridge = OpenFeatureEvaluationBridge(WorkingProvider())
    first = bridge.get_boolean_details("feature-x", False, {"targetingKey": "user-1"})
    second = bridge.get_boolean_details("feature-x", False, {"targetingKey": "user-1"})
    other = bridge.get_boolean_details("feature-x", False, {"targetingKey": "user-2"})
    assert first.evidence_digest == second.evidence_digest
    assert first.evidence_digest != other.evidence_digest


def test_provider_metadata_name_is_required() -> None:
    try:
        ProviderMetadata("   ")
    except ValueError as exc:
        assert "provider name" in str(exc)
    else:
        raise AssertionError("empty provider name must fail")
