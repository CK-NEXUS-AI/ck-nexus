from __future__ import annotations

import json

import pytest

from creator_app.connector_fabric.evidence import ConnectorEvidenceLedger
from creator_app.connector_fabric.fabric import (
    ConnectorActivationDecision,
    ConnectorFabric,
)
from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorProtocol,
    ConnectorState,
    DiscoverySnapshot,
    NormalizedTool,
    RiskClass,
)
from creator_app.connector_fabric.registry import ConnectorRegistry


def _tool(name: str, risk: RiskClass) -> NormalizedTool:
    return NormalizedTool(
        connector_id="demo",
        name=name,
        description=name,
        input_schema={"type": "object", "properties": {}},
        annotations={"readOnlyHint": risk is RiskClass.READ_ONLY},
        risk=risk,
    )


def _fabric(tmp_path, risks: tuple[RiskClass, ...], *, activation_authorizer=None):
    registry = ConnectorRegistry(tmp_path / "registry.json")
    registry.register(
        ConnectorConfig(
            connector_id="demo",
            url="https://example.com/mcp",
            protocol=ConnectorProtocol.MCP,
        )
    )
    snapshot = DiscoverySnapshot(
        connector_id="demo",
        protocol=ConnectorProtocol.MCP,
        protocol_version="stress-lab-v1",
        tools=tuple(_tool(f"tool_{index}", risk) for index, risk in enumerate(risks)),
        schema_hash="a" * 64,
    )
    registry.set_snapshot(snapshot)
    ledger = ConnectorEvidenceLedger(tmp_path / "evidence.jsonl")
    fabric = ConnectorFabric(
        registry=registry,
        evidence=ledger,
        activation_authorizer=activation_authorizer,
    )
    return fabric, registry, ledger.path


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_write_activation_fails_closed_without_separate_authority(tmp_path):
    fabric, registry, evidence_path = _fabric(
        tmp_path,
        (RiskClass.READ_ONLY, RiskClass.WRITE),
    )

    with pytest.raises(PermissionError, match="write activation denied"):
        fabric.activate("demo", allow_write=True)

    assert registry.get("demo").state is ConnectorState.SCHEMA_VERIFIED
    event = _events(evidence_path)[-1]
    assert event["event"] == "connector.activation_denied"
    assert event["details"]["requestedMode"] == "ACTIVE_WRITE"
    assert event["details"]["schemaHash"] == "a" * 64


def test_read_only_activation_does_not_require_write_authority(tmp_path):
    fabric, registry, _ = _fabric(
        tmp_path,
        (RiskClass.READ_ONLY, RiskClass.WRITE),
    )

    record = fabric.activate("demo")

    assert record.state is ConnectorState.ACTIVE_READ_ONLY
    assert registry.get("demo").state is ConnectorState.ACTIVE_READ_ONLY
    assert [tool["name"] for tool in fabric.model_tools("demo")] == ["demo.tool_0"]


class AllowWriteActivationAuthorizer:
    def __init__(self) -> None:
        self.calls = 0

    def authorize_activation(self, **kwargs):
        self.calls += 1
        assert kwargs["requested_state"] is ConnectorState.ACTIVE_WRITE
        assert kwargs["snapshot"].schema_hash == "a" * 64
        return ConnectorActivationDecision(
            True,
            "stress-lab approval",
            approval_ref="EVD-STRESS-L2-001",
        )


def test_approved_write_activation_still_does_not_grant_tool_execution(tmp_path):
    activation_authorizer = AllowWriteActivationAuthorizer()
    fabric, registry, evidence_path = _fabric(
        tmp_path,
        (RiskClass.READ_ONLY, RiskClass.WRITE),
        activation_authorizer=activation_authorizer,
    )

    record = fabric.activate(
        "demo",
        allow_write=True,
        context={"taskId": "CKT-002"},
    )

    assert activation_authorizer.calls == 1
    assert record.state is ConnectorState.ACTIVE_WRITE
    assert registry.get("demo").state is ConnectorState.ACTIVE_WRITE
    assert [tool["name"] for tool in fabric.model_tools("demo")] == [
        "demo.tool_0",
        "demo.tool_1",
    ]
    approved = [
        event for event in _events(evidence_path) if event["event"] == "connector.write_activation_approved"
    ]
    assert approved[-1]["details"]["approvalRef"] == "EVD-STRESS-L2-001"

    with pytest.raises(PermissionError, match="execution denied"):
        fabric.invoke("demo", "tool_1", {})


class NeverCalledActivationAuthorizer:
    def __init__(self) -> None:
        self.calls = 0

    def authorize_activation(self, **kwargs):
        self.calls += 1
        return ConnectorActivationDecision(True, "should not be reached")


def test_unknown_risk_blocks_write_activation_before_authorizer(tmp_path):
    activation_authorizer = NeverCalledActivationAuthorizer()
    fabric, registry, evidence_path = _fabric(
        tmp_path,
        (RiskClass.READ_ONLY, RiskClass.UNKNOWN),
        activation_authorizer=activation_authorizer,
    )

    with pytest.raises(PermissionError, match="Unknown-risk"):
        fabric.activate("demo", allow_write=True)

    assert activation_authorizer.calls == 0
    assert registry.get("demo").state is ConnectorState.SCHEMA_VERIFIED
    event = _events(evidence_path)[-1]
    assert event["event"] == "connector.activation_denied"
    assert event["details"]["unknownRiskToolCount"] == 1
