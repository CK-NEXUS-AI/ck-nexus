import pytest

from creator_app.core.policy_errors import PolicyViolation
from creator_app.core.ultra_capability_governance import (
    CapabilityRecord,
    CapabilityState,
    UltraCapabilityRegistry,
    build_default_ultra_registry,
)
from creator_app.core.ultra_command_router import UltraCommandRouter


def test_unknown_capability_is_not_available() -> None:
    registry = build_default_ultra_registry()
    record = registry.get("/unknown")
    assert record.state == CapabilityState.NOT_AVAILABLE
    assert registry.truthful_status("/unknown") == "NOT_AVAILABLE"


def test_verified_without_executor_is_not_ready() -> None:
    registry = build_default_ultra_registry()
    record = registry.get("/formal")
    assert record.state == CapabilityState.VERIFIED
    assert record.executor_available is False
    assert record.ready is False
    assert registry.truthful_status("/formal") == "VERIFIED_NO_EXECUTOR"


def test_chaos_requires_governor_approval() -> None:
    router = UltraCommandRouter()
    with pytest.raises(PolicyViolation):
        router.execute("/chaos")

    result = router.execute("/chaos", governor_approved=True)
    assert result.status == "READY_VERIFIED"
    assert result.executable is True


def test_sales_is_blocked_and_never_becomes_prompt_authority() -> None:
    router = UltraCommandRouter()
    with pytest.raises(PolicyViolation):
        router.execute("/sales", governor_approved=True)


def test_think_is_explicitly_simulated() -> None:
    result = UltraCommandRouter().execute("/think")
    assert result.simulated is True
    assert result.executable is False
    assert result.status == "SIMULATED"


def test_duplicate_command_rejected() -> None:
    registry = UltraCapabilityRegistry()
    record = CapabilityRecord(
        capability_id="x",
        command="/x",
        description="x",
        state=CapabilityState.IMPLEMENTED_UNVERIFIED,
    )
    registry.register(record)
    with pytest.raises(ValueError):
        registry.register(record)
