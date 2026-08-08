from creator_app.health import (
    DependencyState,
    DependencyStatus,
    HealthCause,
    HealthState,
    evaluate_health,
)


def test_live_without_dependencies() -> None:
    report = evaluate_health()
    assert report.state is HealthState.LIVE
    assert report.live is True
    assert report.ready is True
    assert report.degraded is False


def test_all_required_dependencies_make_service_ready() -> None:
    report = evaluate_health(
        [
            DependencyStatus("database", DependencyState.HEALTHY),
            DependencyStatus("workflow", DependencyState.HEALTHY),
        ]
    )
    assert report.state is HealthState.READY
    assert report.ready is True
    assert report.causes == ()


def test_required_failure_blocks_readiness_with_stable_cause_code() -> None:
    report = evaluate_health(
        [DependencyStatus("database", DependencyState.UNAVAILABLE, required=True)]
    )
    assert report.state is HealthState.DEGRADED
    assert report.ready is False
    assert report.causes == (HealthCause.REQUIRED_DEPENDENCY_UNAVAILABLE,)


def test_optional_failure_degrades_without_blocking_readiness() -> None:
    report = evaluate_health(
        [
            DependencyStatus("database", DependencyState.HEALTHY),
            DependencyStatus("openai", DependencyState.UNAVAILABLE, required=False),
        ]
    )
    assert report.ready is True
    assert report.degraded is True
    assert HealthCause.OPTIONAL_DEPENDENCY_UNAVAILABLE in report.causes


def test_optional_disabled_dependency_is_not_a_failure() -> None:
    report = evaluate_health(
        [DependencyStatus("github", DependencyState.DISABLED, required=False)]
    )
    assert report.state is HealthState.READY
    assert report.ready is True
    assert report.degraded is False


def test_process_not_live_is_never_ready() -> None:
    report = evaluate_health(process_live=False)
    assert report.state is HealthState.DEGRADED
    assert report.live is False
    assert report.ready is False
    assert report.causes == (HealthCause.PROCESS_NOT_LIVE,)


def test_health_serialization_contains_no_free_form_dependency_details() -> None:
    report = evaluate_health([DependencyStatus("database", DependencyState.HEALTHY)])
    payload = report.as_dict()
    assert payload["state"] == "ready"
    assert payload["dependencies"] == [
        {"name": "database", "state": "healthy", "required": True}
    ]
