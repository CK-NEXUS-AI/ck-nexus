"""Tests for Gmail Universal Bridge without live credentials."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from creator_app.credentials.gmail_universal_bridge import (
    ForwardTarget,
    GmailBridgeError,
    GmailUniversalBridge,
)


@pytest.fixture
def mock_api_client():
    """Return a deterministic Gmail API mock with no live credentials."""
    client = MagicMock()
    client.list_messages.return_value = [{"id": "msg1"}, {"id": "msg2"}]

    def get_message(msg_id):
        if msg_id == "msg1":
            return {
                "id": "msg1",
                "threadId": "thread1",
                "snippet": (
                    "Your verification code is 123456. "
                    "Open https://example.com/verify?code=123456 to confirm."
                ),
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
        if msg_id == "msg2":
            return {
                "id": "msg2",
                "threadId": "thread2",
                "snippet": "OTP Login Code: 654321",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "OTP Login Code"},
                        {"name": "From", "value": "security@example.com"},
                        {"name": "To", "value": "user@example.com"},
                    ],
                    "parts": [],
                },
            }
        return {}

    client.get_message.side_effect = get_message
    client.send_message.return_value = "new_msg_id_123"
    return client


@pytest.mark.asyncio
async def test_gmail_bridge_authenticate_with_mock(mock_api_client):
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    assert await bridge.authenticate() is True
    assert bridge.is_authenticated


@pytest.mark.asyncio
async def test_gmail_bridge_authenticate_no_credentials():
    bridge = GmailUniversalBridge()
    assert await bridge.authenticate() is False
    assert not bridge.is_authenticated


def test_gmail_bridge_list_unread_emails(mock_api_client):
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    emails = bridge.list_unread_emails()
    assert len(emails) == 2
    assert emails[0].subject == "Verify your account"
    assert "123456" in emails[0].snippet


def test_gmail_bridge_extract_otp(mock_api_client):
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    extracted = bridge.extract_otp_and_links(bridge.list_unread_emails()[0])
    assert "123456" in extracted.otp_codes


def test_gmail_bridge_extract_verification_links(mock_api_client):
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    extracted = bridge.extract_otp_and_links(bridge.list_unread_emails()[0])
    assert extracted.verification_links
    assert any("verify" in link.lower() for link in extracted.verification_links)


def test_gmail_bridge_send_email(mock_api_client):
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
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    results = bridge.process_new_emails()
    assert results["total"] == 2
    assert results["processed"] == 2
    assert results["otp_found"] >= 1


def test_gmail_bridge_forward_to_system(mock_api_client):
    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    email = bridge.list_unread_emails()[0]
    extracted = bridge.extract_otp_and_links(email)
    result = bridge.forward_to_system(email, extracted)
    assert result["status"] == "forwarded"
    assert "extracted" in result["payload"]


def test_gmail_bridge_not_authenticated_raises():
    bridge = GmailUniversalBridge()
    with pytest.raises(GmailBridgeError):
        bridge.list_unread_emails()


def test_gmail_bridge_register_forward_target(mock_api_client):
    forwarded = []

    def forward_func(email, extracted):
        forwarded.append({"subject": email.subject, "otps": list(extracted.otp_codes)})

    bridge = GmailUniversalBridge(api_client=mock_api_client)
    asyncio.run(bridge.authenticate())
    bridge.register_forward_target(
        ForwardTarget(name="telegram_alerts", forward_func=forward_func)
    )
    bridge.process_new_emails()
    assert forwarded
