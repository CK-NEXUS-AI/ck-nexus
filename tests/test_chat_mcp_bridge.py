import pytest

from creator_app.core.chat_bridge import (
    BridgeCommand,
    BridgeMode,
    CKNexusChatBridge,
    ChatBridgePolicy,
)
from creator_app.core.mcp_bridge_manifest import build_manifest


def test_bridge_defaults_disabled() -> None:
    bridge = CKNexusChatBridge()
    assert bridge.policy.mode == BridgeMode.DISABLED
    with pytest.raises(PermissionError):
        bridge.execute(BridgeCommand(command="status"))


def test_enable_requires_governor() -> None:
    bridge = CKNexusChatBridge()
    with pytest.raises(PermissionError):
        bridge.enable_read_only(governor_approved=False)


def test_read_only_status_command() -> None:
    bridge = CKNexusChatBridge()
    bridge.register_read_handler("status", lambda args: {"system": "CK-NEXUS"})
    bridge.enable_read_only(governor_approved=True)

    result = bridge.execute(BridgeCommand(command="status"))

    assert result.status == "OK"
    assert result.live_executed is True
    assert result.data["system"] == "CK-NEXUS"


def test_unknown_command_is_blocked() -> None:
    bridge = CKNexusChatBridge()
    bridge.enable_read_only(governor_approved=True)
    with pytest.raises(PermissionError):
        bridge.execute(BridgeCommand(command="deploy"))


def test_policy_weakening_fails_closed() -> None:
    policy = ChatBridgePolicy(production_mutation_allowed=True)
    bridge = CKNexusChatBridge(policy)
    bridge.enable_read_only(governor_approved=True)
    with pytest.raises(RuntimeError):
        bridge.execute(BridgeCommand(command="status"))


def test_manifest_is_safe_by_default() -> None:
    manifest = build_manifest()
    assert manifest.default_enabled is False
    assert manifest.read_only is True
    assert manifest.production_mutation_allowed is False
    assert manifest.external_write_allowed is False
    assert manifest.requires_governor_approval is True
