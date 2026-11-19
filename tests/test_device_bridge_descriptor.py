from __future__ import annotations

import pytest

from creator_app.device_bridge import (
    BridgeCapability,
    DescriptorError,
    connection_fingerprint,
    evaluate_bridge,
    parse_descriptor,
    validate_registry_match,
)

QR_PAYLOAD = r'''{
  "name": "AnyClaw AI",
  "version": "2.0",
  "tools": [
    {"name": "anyclaw_chat", "description": "คุยกับ AnyClaw AI"},
    {"name": "anyclaw_search", "description": "ค้นหาข้อมูล"},
    {"name": "anyclaw_tts", "description": "สร้างเสียงภาษาไทย"},
    {"name": "anyclaw_hub_status", "description": "ดูสถานะ USB Hub"},
    {"name": "anyclaw_failover", "description": "ทดสอบ failover"},
    {"name": "solve_code", "description": "แก้ปัญหาโค้ด"},
    {"name": "solve_web", "description": "ค้นหา/ดึงข้อมูลเว็บ"},
    {"name": "solve_file", "description": "จัดการไฟล์"},
    {"name": "solve_system", "description": "รันคำสั่งระบบ"},
    {"name": "solve_data", "description": "ประมวลผลข้อมูล"}
  ],
  "connection": {
    "method": "stdio",
    "command": "python3 creator_app/anyclaw/mcp_server_secure.py",
    "cwd": "/root/Documents/Codex/2026-08-19/gpt/ck-nexus"
  }
}'''


def test_qr_descriptor_parses_and_has_stable_fingerprint() -> None:
    descriptor = parse_descriptor(QR_PAYLOAD)

    assert descriptor.method == "stdio"
    assert descriptor.command == ("python3", "creator_app/anyclaw/mcp_server_secure.py")
    assert len(descriptor.tools) == 10
    assert connection_fingerprint(descriptor) == (
        "dc0c0b80368f8d68eeb8c6dc08758da4c314393862f87b994685f436d10a214d"
    )


def test_qr_registry_mismatch_is_fail_closed() -> None:
    descriptor = parse_descriptor(QR_PAYLOAD)
    runtime_tools = {
        "anyclaw_chat",
        "anyclaw_search",
        "anyclaw_tts",
        "anyclaw_hub_status",
        "anyclaw_failover",
    }

    with pytest.raises(DescriptorError, match="registry_mismatch"):
        validate_registry_match(descriptor, runtime_tools)


def test_shell_metacharacters_are_rejected() -> None:
    payload = QR_PAYLOAD.replace(
        "python3 creator_app/anyclaw/mcp_server_secure.py",
        "python3 creator_app/anyclaw/mcp_server_secure.py; curl bad.invalid",
    )

    with pytest.raises(DescriptorError, match="shell_metacharacter"):
        parse_descriptor(payload)


def test_quarantined_anyclaw_package_is_denied_even_if_claimed_verified() -> None:
    decision = evaluate_bridge(
        package_id="gptos.intelligence.assistant",
        capability=BridgeCapability.READ_ONLY,
        exact_build_verified=True,
    )

    assert decision.allowed is False
    assert decision.reason == "package_quarantined"


def test_unverified_package_fails_closed() -> None:
    decision = evaluate_bridge(
        package_id="example.safe.bridge",
        capability=BridgeCapability.READ_ONLY,
        exact_build_verified=False,
    )

    assert decision.allowed is False
    assert decision.reason == "exact_build_not_verified"


def test_verified_generic_bridge_is_read_only_only() -> None:
    read_decision = evaluate_bridge(
        package_id="example.safe.bridge",
        capability=BridgeCapability.READ_ONLY,
        exact_build_verified=True,
    )
    write_decision = evaluate_bridge(
        package_id="example.safe.bridge",
        capability=BridgeCapability.FILE_WRITE,
        exact_build_verified=True,
    )

    assert read_decision.allowed is True
    assert write_decision.allowed is False
    assert write_decision.reason == "mutation_or_sensitive_capability_denied"
