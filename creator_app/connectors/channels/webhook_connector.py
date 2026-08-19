"""Webhook Connector — รับ/ส่ง HTTP webhooks."""

from __future__ import annotations

import hashlib
import json
import time


class WebhookConnector:
    """Generic Webhook — รับ/ส่ง HTTP callbacks.

    วิธีใช้:
        wh = WebhookConnector(secret="my_secret")
        payload = wh.receive(headers, body)
        if payload:
            # ประมวลผล
            wh.send("https://example.com/hook", {"status": "ok"})
    """

    def __init__(self, secret: str = ""):
        self._secret = secret
        self._received: list[dict] = []

    def receive(self, headers: dict, body: str) -> dict | None:
        """รับ webhook payload — verify signature ถ้ามี secret."""
        if self._secret:
            sig = headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hashlib.sha256(
                (self._secret + body).encode()
            ).hexdigest()
            if sig != expected:
                return None
        try:
            payload = json.loads(body)
            self._received.append({
                "timestamp": time.time(),
                "payload": payload,
            })
            return payload
        except (json.JSONDecodeError, TypeError):
            return None

    def send(self, url: str, data: dict) -> dict:
        """ส่ง webhook ไปยัง URL."""
        import requests
        try:
            resp = requests.post(url, json=data, timeout=10)
            return {"status_code": resp.status_code, "ok": resp.ok}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @property
    def received_count(self) -> int:
        return len(self._received)
