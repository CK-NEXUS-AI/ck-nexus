"""Tests for connector lifecycle, continuity, proactive policy and observability."""

from datetime import UTC, datetime, time

import pytest

from creator_app.channel_continuity import (
    ChannelSession,
    ConversationContinuityRegistry,
    conversation_id_for,
)
from creator_app.connector_fabric_v2 import (
    CapabilityMode,
    ConnectorCapability,
    ConnectorLifecycleError,
    ConnectorRecord,
    ConnectorRegistry,
    ConnectorState,
)
from creator_app.data_governance import DEFAULT_DATA_POLICIES, StorageMode, require_purpose
from creator_app.evaluation_framework import (
    RED_TEAM_VECTORS,
    EvaluationDimension,
    EvaluationScore,
    EvaluationScorecard,
)
from creator_app.observability_v2 import MetricRegistry, TelemetryEvent, redact_diagnostic
from creator_app.proactive_assistant import (
    ProactiveController,
    ProactivePolicy,
    ProactiveProposal,
    ProactiveStage,
)
from creator_app.privacy_firewall import DataClassification
from creator_app.tool_trust import ToolDescriptor, ToolTrustDenied, ToolTrustRegistry, ToolTrustState


def test_connector_lifecycle_separates_discovery_auth_and_availability() -> None:
    registry = ConnectorRegistry()
    record = ConnectorRecord(
        connector_id="gmail-user-a",
        provider="gmail",
        tenant_id="tenant-a",
        state=ConnectorState.DISCOVERED,
    )
    registry.add(record)
    assert registry.capability_allowed(
        record.connector_id,
        "gmail.metadata.read",
        mode=CapabilityMode.READ,
    ) is False
    registry.transition(record.connector_id, ConnectorState.CONFIGURED)
    registry.transition(record.connector_id, ConnectorState.AUTHENTICATED)
    registry.bind_authorization(
        record.connector_id,
        scopes=("metadata",),
        capabilities=(
            ConnectorCapability("gmail.metadata.read", CapabilityMode.READ),
        ),
        credential_ref="cred://gmail/user-a",
    )
    registry.transition(record.connector_id, ConnectorState.HEALTHY)
    registry.transition(record.connector_id, ConnectorState.AVAILABLE)
    assert registry.capability_allowed(
        record.connector_id,
        "gmail.metadata.read",
        mode=CapabilityMode.READ,
    ) is True
    assert registry.capability_allowed(
        record.connector_id,
        "gmail.send",
        mode=CapabilityMode.WRITE,
    ) is False


def test_connector_cannot_skip_authentication_or_use_raw_credential() -> None:
    registry = ConnectorRegistry()
    registry.add(
        ConnectorRecord(
            connector_id="x",
            provider="x",
            tenant_id="t",
            state=ConnectorState.DISCOVERED,
        )
    )
    with pytest.raises(ConnectorLifecycleError):
        registry.transition("x", ConnectorState.AUTHORIZED)
    registry.transition("x", ConnectorState.CONFIGURED)
    registry.transition("x", ConnectorState.AUTHENTICATED)
    with pytest.raises(ValueError, match="cred://"):
        registry.bind_authorization(
            "x",
            scopes=("read",),
            capabilities=(),
            credential_ref="raw-token",
        )


def test_conversation_continuity_links_channels_without_duplicate_source() -> None:
    registry = ConversationContinuityRegistry()
    conversation_id = conversation_id_for(tenant_id="t", user_id="u", seed="seed")
    registry.bind(ChannelSession("web", "web-1", conversation_id, "t", "u"))
    registry.bind(ChannelSession("gmail", "thread-1", conversation_id, "t", "u"))
    assert registry.resolve("gmail", "thread-1").conversation_id == conversation_id
    assert registry.seen_source(conversation_id, "gmail:m1", "hello") is False
    assert registry.seen_source(conversation_id, "gmail:m1", "hello") is True


def test_proactive_assistant_is_opt_in_bounded_and_approval_first() -> None:
    disabled = ProactiveController(ProactivePolicy(enabled=False))
    proposal = ProactiveProposal("deadline", 0.95, "web")
    assert disabled.decide(proposal).allowed is False

    policy = ProactivePolicy(
        enabled=True,
        quiet_start=time(23, 0),
        quiet_end=time(7, 0),
        max_notifications_per_day=1,
        allowed_channels=frozenset({"web"}),
    )
    controller = ProactiveController(policy)
    daytime = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
    decision = controller.decide(proposal, now=daytime)
    assert decision.allowed is True
    exhausted = controller.decide(proposal, now=daytime)
    assert exhausted.reason == "daily_notification_budget_exhausted"


def test_proactive_external_write_requires_explicit_approval() -> None:
    controller = ProactiveController(
        ProactivePolicy(enabled=True, allowed_channels=frozenset({"gmail"}))
    )
    proposal = ProactiveProposal(
        "followup",
        0.99,
        "gmail",
        stage=ProactiveStage.EXECUTE,
        external_write=True,
    )
    denied = controller.decide(proposal, approved=False)
    assert denied.allowed is False
    assert denied.approval_required is True
    assert controller.decide(proposal, approved=True).allowed is True


def test_tool_discovery_always_enters_quarantine_before_trust() -> None:
    registry = ToolTrustRegistry()
    tool = registry.discover(
        ToolDescriptor(
            tool_id="mcp.search",
            provider="remote-mcp",
            version="1.0.0",
            schema_hash="a" * 64,
            source="https://example.invalid/mcp",
            permissions=("search",),
        )
    )
    assert tool.state == ToolTrustState.QUARANTINED
    with pytest.raises(ToolTrustDenied):
        registry.require(tool.tool_id)
    registry.set_state(tool.tool_id, ToolTrustState.REVIEWED)
    registry.set_state(tool.tool_id, ToolTrustState.TRUSTED_READ)
    assert registry.require(tool.tool_id).state == ToolTrustState.TRUSTED_READ
    with pytest.raises(ToolTrustDenied):
        registry.require(tool.tool_id, write=True)


def test_revoked_tool_cannot_be_reactivated() -> None:
    registry = ToolTrustRegistry()
    registry.discover(
        ToolDescriptor(
            tool_id="tool-x",
            provider="p",
            version="1",
            schema_hash="b" * 64,
            source="source",
            permissions=(),
        )
    )
    registry.set_state("tool-x", ToolTrustState.REVOKED)
    with pytest.raises(ToolTrustDenied, match="reactivated"):
        registry.set_state("tool-x", ToolTrustState.TRUSTED_READ)


def test_observability_redacts_and_cannot_claim_audit_authority() -> None:
    diagnostic = redact_diagnostic(
        "gmail",
        "error",
        "failed for person@example.com with token " + "sk-" + "a" * 24,
    )
    assert "person@example.com" not in diagnostic.safe_message
    assert "sk-" + "a" * 24 not in diagnostic.safe_message
    registry = MetricRegistry()
    registry.record(TelemetryEvent("latency", 10.0, "ms", "gmail", "corr-1"))
    assert len(registry.snapshot(component="gmail")) == 1
    with pytest.raises(ValueError, match="audit authority"):
        registry.record(
            TelemetryEvent(
                "security_event",
                1.0,
                "count",
                "policy",
                "corr-2",
                audit_authority=True,
            )
        )


def test_evaluation_scorecard_and_red_team_inventory_are_bounded() -> None:
    scorecard = EvaluationScorecard(
        "subject",
        (
            EvaluationScore(EvaluationDimension.QUALITY, 0.8, "evd-1", "judge-a"),
            EvaluationScore(EvaluationDimension.SECURITY, 1.0, "evd-2", "verifier"),
        ),
    )
    assert scorecard.weighted({EvaluationDimension.SECURITY: 2.0}) > 0.8
    attack_classes = {vector.attack_class for vector in RED_TEAM_VECTORS}
    assert "prompt_injection" in attack_classes
    assert "cross_tenant_access" in attack_classes
    assert "credential_exfiltration" in attack_classes


def test_data_governance_minimizes_secret_and_sensitive_storage() -> None:
    secret = DEFAULT_DATA_POLICIES[DataClassification.SECRET]
    sensitive = DEFAULT_DATA_POLICIES[DataClassification.SENSITIVE]
    assert secret.storage == StorageMode.FORBIDDEN
    assert secret.external_sharing is False
    assert sensitive.storage == StorageMode.EPHEMERAL
    assert sensitive.consent_required is True
    with pytest.raises(PermissionError, match="purpose"):
        require_purpose(DataClassification.PERSONAL, "advertising")
