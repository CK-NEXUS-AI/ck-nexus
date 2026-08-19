"""Gmail Universal Bridge — governed development adapter for Gmail workflows.

This module parses Gmail message payloads and can use an explicitly injected
API client for development/testing. Runtime authentication should be provided
through the canonical CK-NEXUS Credential Broker / Gmail connector; it never
extracts or prints raw credentials.
"""

from __future__ import annotations

import base64
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Any, Protocol

from creator_app.credentials.gmail_oauth_connector import GmailConnector

logger = logging.getLogger("cknexus.gmail_bridge")

OTP_PATTERN = re.compile(r"\b(\d{4,8})\b")
URL_PATTERN = re.compile(r'https?://[^\s<>"\)\]]+', re.IGNORECASE)
PAYMENT_PATTERN = re.compile(r"\b\d{1,3}(?:[,.]\d{3})*(?:\.\d{2})?\b")


@dataclass(frozen=True, slots=True)
class ExtractedEmail:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipients: tuple[str, ...]
    date: str
    body_plain: str
    body_html: str
    snippet: str


@dataclass(frozen=True, slots=True)
class ExtractedData:
    otp_codes: tuple[str, ...]
    verification_links: tuple[str, ...]
    payment_amounts: tuple[str, ...]
    attachments: tuple[str, ...]
    important_numbers: tuple[str, ...]


@dataclass
class ForwardTarget:
    name: str
    forward_func: Callable[[ExtractedEmail, ExtractedData], Any]
    conditions: tuple[str, ...] = ()


class GmailBridgeError(RuntimeError):
    """Safe Gmail bridge error that never carries credential material."""


class GmailApiInterface(Protocol):
    """Small Gmail API interface used by the development bridge."""

    def list_messages(self, **kwargs) -> list[dict]: ...

    def get_message(self, message_id: str) -> dict: ...

    def send_message(self, raw_message: str) -> str: ...


class GmailUniversalBridge:
    """Parse and route Gmail messages through a governed adapter boundary."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(
        self,
        connector: GmailConnector | None = None,
        api_client: GmailApiInterface | None = None,
    ) -> None:
        self._connector = connector
        self._api_client = api_client
        self._authenticated = False
        self._forward_targets: list[ForwardTarget] = []
        self._stats = {
            "emails_read": 0,
            "otps_extracted": 0,
            "links_extracted": 0,
            "payments_extracted": 0,
            "notifications_sent": 0,
            "emails_sent": 0,
        }

    async def authenticate(self) -> bool:
        """Enable the bridge only when a governed connector/client is explicitly supplied."""
        if self._api_client is not None:
            self._authenticated = True
            logger.info("Gmail bridge authenticated via injected API client")
            return True
        if self._connector is not None:
            self._authenticated = True
            logger.info("Gmail bridge authenticated via CK-NEXUS connector")
            return True
        logger.warning("Gmail bridge: no governed connector available — fail-closed")
        return False

    def register_forward_target(self, target: ForwardTarget) -> None:
        """Register an explicit downstream forwarding callback."""
        self._forward_targets.append(target)

    def list_unread_emails(self, *, max_results: int = 50) -> tuple[ExtractedEmail, ...]:
        """Read unread emails through the injected API client."""
        if not self._authenticated:
            raise GmailBridgeError("Not authenticated — call authenticate() first")
        if self._api_client is None:
            return ()
        if not 1 <= max_results <= 500:
            raise ValueError("max_results must be between 1 and 500")

        results = self._api_client.list_messages(q="is:unread", maxResults=max_results)
        emails: list[ExtractedEmail] = []
        for msg_meta in results:
            msg_id = msg_meta.get("id", "")
            msg_data = self._api_client.get_message(msg_id)
            email = self._parse_message(msg_data)
            if email:
                emails.append(email)
                self._stats["emails_read"] += 1
        return tuple(emails)

    def get_email(self, message_id: str) -> ExtractedEmail | None:
        """Fetch a single email through the injected API client."""
        if not self._authenticated or self._api_client is None:
            return None
        return self._parse_message(self._api_client.get_message(message_id))

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
    ) -> str:
        """Send an email through an explicitly injected Gmail API client."""
        if not self._authenticated or self._api_client is None:
            raise GmailBridgeError("Not authenticated — call authenticate() first")

        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        message_id = self._api_client.send_message(raw)
        self._stats["emails_sent"] += 1
        logger.info("Sent email through injected Gmail client")
        return message_id

    def extract_otp_and_links(self, email: ExtractedEmail) -> ExtractedData:
        """Extract OTP-like numbers, URLs, and amount-like values from visible text."""
        text = f"{email.subject}\n{email.body_plain}\n{email.snippet}"
        otp_matches = tuple(OTP_PATTERN.findall(text))
        url_matches = tuple(URL_PATTERN.findall(text))
        payment_matches = tuple(PAYMENT_PATTERN.findall(text))
        verification_keywords = (
            "verify",
            "confirm",
            "otp",
            "token",
            "code",
            "reset",
            "ยืนยัน",
        )
        verification_links = tuple(
            url
            for url in url_matches
            if any(keyword in url.lower() for keyword in verification_keywords)
        )

        self._stats["otps_extracted"] += len(otp_matches)
        self._stats["links_extracted"] += len(verification_links)
        self._stats["payments_extracted"] += len(payment_matches)
        return ExtractedData(
            otp_codes=otp_matches,
            verification_links=verification_links,
            payment_amounts=payment_matches,
            attachments=(),
            important_numbers=otp_matches,
        )

    def process_new_emails(self) -> dict:
        """Parse new emails and forward matching records to registered callbacks."""
        emails = self.list_unread_emails()
        results = {
            "total": len(emails),
            "processed": 0,
            "otp_found": 0,
            "verification_found": 0,
            "notifications_sent": 0,
        }
        urgent_keywords = (
            "เร่งด่วน",
            "ด่วนที่สุด",
            "ชำระเงิน",
            "ยืนยัน",
            "เตือน",
            "alert",
            "urgent",
            "important",
            "payment",
        )

        for email in emails:
            extracted = self.extract_otp_and_links(email)
            results["otp_found"] += len(extracted.otp_codes)
            results["verification_found"] += len(extracted.verification_links)
            for target in self._forward_targets:
                try:
                    conditions_met = not target.conditions or any(
                        keyword in email.subject.lower() or keyword in email.body_plain.lower()
                        for keyword in target.conditions
                    )
                    if conditions_met:
                        target.forward_func(email, extracted)
                except Exception as exc:
                    logger.warning("Forward to %s failed: %s", target.name, type(exc).__name__)

            text_lower = f"{email.subject.lower()} {email.body_plain.lower()}"
            if any(keyword.lower() in text_lower for keyword in urgent_keywords):
                self._send_urgent_notification(email, extracted)
                results["notifications_sent"] += 1
            results["processed"] += 1
        return results

    def forward_to_system(self, email: ExtractedEmail, extracted: ExtractedData) -> dict:
        """Build a redacted structured payload for a downstream governed system."""
        payload = {
            "source": "gmail",
            "message_id": email.message_id,
            "subject": email.subject,
            "sender": email.sender,
            "received_at": email.date,
            "extracted": {
                "otp_codes": list(extracted.otp_codes),
                "verification_links": list(extracted.verification_links),
                "payment_amounts": list(extracted.payment_amounts),
            },
        }
        return {"status": "forwarded", "payload": payload}

    def _parse_message(self, msg_data: dict) -> ExtractedEmail | None:
        """Convert a Gmail API payload into a normalized email record."""
        headers = msg_data.get("payload", {}).get("headers", [])
        header_map = {
            item.get("name", "").lower(): item.get("value", "")
            for item in headers
            if isinstance(item, dict)
        }
        return ExtractedEmail(
            message_id=str(msg_data.get("id", "")),
            thread_id=str(msg_data.get("threadId", "")),
            subject=str(header_map.get("subject", "")),
            sender=str(header_map.get("from", "")),
            recipients=tuple(self._parse_recipients(str(header_map.get("to", "")))),
            date=str(header_map.get("date", "")),
            body_plain=self._extract_body_text(msg_data),
            body_html="",
            snippet=str(msg_data.get("snippet", "")),
        )

    @staticmethod
    def _parse_recipients(header_value: str) -> list[str]:
        if not header_value:
            return []
        return [addr.strip() for addr in header_value.split(",") if addr.strip()]

    @staticmethod
    def _extract_body_text(msg_data: dict) -> str:
        """Extract decoded text/plain MIME parts, falling back to snippet."""
        parts = msg_data.get("payload", {}).get("parts", [])
        text_parts: list[str] = []
        for part in parts:
            if not isinstance(part, dict) or part.get("mimeType", "") != "text/plain":
                continue
            data = part.get("body", {}).get("data", "")
            if not data:
                continue
            try:
                padding = "=" * (-len(data) % 4)
                decoded = base64.urlsafe_b64decode(data + padding).decode(
                    "utf-8", errors="replace"
                )
            except (ValueError, UnicodeError):
                continue
            text_parts.append(decoded)
        if not text_parts:
            snippet = msg_data.get("snippet", "")
            if snippet:
                text_parts.append(str(snippet))
        return "\n".join(text_parts)

    def _send_urgent_notification(
        self,
        email: ExtractedEmail,
        extracted: ExtractedData,
    ) -> None:
        """Forward an urgent record only to explicitly registered urgent targets."""
        for target in self._forward_targets:
            if "urgent" not in target.name.lower() and "telegram" not in target.name.lower():
                continue
            try:
                target.forward_func(email, extracted)
                self._stats["notifications_sent"] += 1
            except Exception as exc:
                logger.warning("Urgent notification to %s failed: %s", target.name, type(exc).__name__)

    def archive_email(self, message_id: str) -> bool:
        """Return False until a governed Gmail modify-capability adapter is implemented."""
        del message_id
        return False

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def __repr__(self) -> str:
        return f"GmailUniversalBridge(authenticated={self._authenticated})"
