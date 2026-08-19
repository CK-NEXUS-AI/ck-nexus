"""Telegram Bot Connector — เชื่อม Telegram รับ/ส่งข้อความ."""

from __future__ import annotations

import os


class TelegramConnector:
    """Telegram Bot — รับ/ส่งข้อความ.

    วิธีใช้:
        tg = TelegramConnector()  # ดึง token จาก .env
        tg.send_message("user_id", "สวัสดี!")
    """

    def __init__(self, bot_token: str | None = None):
        self._token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def send_message(self, chat_id: str, text: str) -> dict:
        """ส่งข้อความ."""
        import requests
        if not self.is_configured:
            return {"ok": False, "error": "Bot token not configured"}
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            return resp.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_updates(self, offset: int = 0) -> list[dict]:
        """ดึงข้อความใหม่."""
        import requests
        if not self.is_configured:
            return []
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{self._token}/getUpdates",
                params={"offset": offset, "timeout": 5},
                timeout=10,
            )
            data = resp.json()
            return data.get("result", [])
        except Exception:
            return []

    def health_check(self) -> dict:
        import requests
        if not self.is_configured:
            return {"provider": "telegram", "available": False, "error": "no token"}
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{self._token}/getMe",
                timeout=5,
            )
            data = resp.json()
            return {
                "provider": "telegram",
                "available": True,
                "bot_name": data.get("result", {}).get("username", ""),
            }
        except Exception as exc:
            return {"provider": "telegram", "available": False, "error": str(exc)}
