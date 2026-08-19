"""Tests for Gmail Universal Bridge — ไม่ใช้ credential จริง."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from creator_app.credentials.gmail_universal_bridge import (
    ForwardTarget,
    GmailBridgeError,
    GmailUniversalBridge,
)


@pytest.fixture
def mock_api_client():
    """สร้าง mock Gmail API client — ไม่ต้องเชื่อม Gmail จริง."""
    client = MagicMock()

    # Mock message listing
    client.list_messages.return_value = [
        {"id": "msg1"},
        {"id": "msg2"},
    ]

    # Mock message data
    def get_message(msg_id):
        if msg_id == "msg1":
            return {
                "id": "msg1",
                "threadId": "thread1",
                "snippet": "Your verification code is 123456",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Verify your account"},
                        {"name": "From", "value": "noreply@example.com"},
                        {"name": "To", "value": "user@example.com"},
                        {"name": "Date", "value": "Mon, 18 Aug 2025 10:00:00 +0000"},
                    ],
                    "parts": [],
                },
            }
        elif msg_id == "msg2":
            return {
                "id": "msg2",
                "threadId": "thread2",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "OTP Login Code"},
                        {"name": "From", "value": "security@bank.com"},
                        {"name": "To", "value": "spinlnw10@gmail.com"},
                    ],
                },
            }
        return {}

    client.get_message.side_effect = get_message
    client.send_message.return_value = "new_msg_id_123"

    return client


@pytest.mark.asyncio
async def test_gmail_bridge_authenticate_with_mock(mock_api_client):
    """เชื่อมต่อ Gmail ผ่าน mock API client."""
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    result = await bridge.authenticate()
    assert result is True
    assert bridge.is_authenticated


@pytest.mark.asyncio
async def test_gmail_bridge_authenticate_no_credentials():
    """เมื่อไม่มี credentials — ควร fail-closed."""
    bridge = GmailUniversalBridge()
    result = await bridge.authenticate()
    assert result is False
    assert not bridge.is_authenticated


def test_gmail_bridge_list_unread_emails(mock_api_client):
    """ทดสอบการอ่านอีเมลที่ยังไม่ได้อ่าน."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    emails = bridge.list_unread_emails()
    assert len(emails) == 2
    assert emails[0].subject == "Verify your account"
    assert "123456" in emails[0].snippet


def test_gmail_bridge_extract_otp(mock_api_client):
    """สกัดรหัส OTP จากอีเมล."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    emails = bridge.list_unread_emails()
    extracted = bridge.extract_otp_and_links(emails[0])

    assert len(extracted.otp_codes) >= 1
    assert "123456" in extracted.otp_codes


def test_gmail_bridge_extract_verification_links(mock_api_client):
    """สกัดลิงก์ยืนยันจากอีเมล."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    emails = bridge.list_unread_emails()
    extracted = bridge.extract_otp_and_links(emails[0])

    assert len(extracted.verification_links) >= 1
    assert any("verify" in link.lower() for link in extracted.verification_links)


def test_gmail_bridge_send_email(mock_api_client):
    """ส่งอีเมลตอบกลับอัตโอโมเติฟ."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    msg_id = bridge.send_email(
        to="customer@example.com",
        subject="Test Subject",
        body="Test body content",
    )
    assert msg_id == "new_msg_id_123"
    assert bridge.stats["emails_sent"] == 1


def test_gmail_bridge_process_new_emails(mock_api_client):
    """ประมวลผลอีเมลใหม่ทั้งหมดอัตโอโมเติฟ."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    results = bridge.process_new_emails()
    assert results["total"] == 2
    assert results["processed"] == 2
    assert results["otp_found"] >= 1


def test_gmail_bridge_forward_to_system(mock_api_client):
    """ส่งข้อมูลอีเมลไปยังระบบอื่น."""
    import asyncio

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())

    emails = bridge.list_unread_emails()
    email = emails[0]
    extracted = bridge.extract_otp_and_links(email)

    result = bridge.forward_to_system(email, extracted)
    assert result["status"] == "forwarded"
    assert "extracted" in result["payload"]


def test_gmail_bridge_not_authenticated_raises():
    """เมื่อไม่ได้รับการ authenticates → ควร raise error."""
    bridge = GmailUniversalBridge()
    with pytest.raises(GmailBridgeError):
        bridge.list_unread_emails()


def test_gmail_bridge_register_forward_target(mock_api_client):
    """ลงทะเบียนระบบปลายหลังสำหรับการส่งข้อมูลต่อไป."""
    import asyncio

    forwarded = []

    def forward_func(email, extracted):
        forwarded.append({"subject": email.subject, "otps": list(extracted.otp_codes)})

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    bridge.register_forward_target(
        ForwardTarget(
            name="telegram_alerts",
            forward_func=forward_func,
        )
    )

    bridge.process_new_emails()
    assert len(forwarded) > 0
