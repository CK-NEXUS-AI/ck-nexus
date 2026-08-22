from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

JsonRequest = Callable[[str, dict[str, Any] | None, dict[str, str] | None], dict[str, Any]]


def _default_json_request(
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers)
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True, slots=True)
class TelegramBridgeConfig:
    bot_token: str
    ck_api_base: str = "http://127.0.0.1:8000"
    ck_access_token: str = ""
    allowed_chat_ids: frozenset[int] = frozenset()
    default_agent_id: str = "general"

    @classmethod
    def from_env(cls) -> "TelegramBridgeConfig":
        raw_allow = os.getenv("CKNEXUS_TELEGRAM_ALLOWED_CHAT_IDS", "")
        allowed = frozenset(
            int(value.strip())
            for value in raw_allow.split(",")
            if value.strip()
        )
        return cls(
            bot_token=os.getenv("CKNEXUS_TELEGRAM_BOT_TOKEN", "").strip(),
            ck_api_base=os.getenv("CKNEXUS_API_BASE", "http://127.0.0.1:8000").rstrip("/"),
            ck_access_token=os.getenv("CKNEXUS_ACCESS_TOKEN", "").strip(),
            allowed_chat_ids=allowed,
            default_agent_id=os.getenv("CKNEXUS_TELEGRAM_AGENT_ID", "general").strip() or "general",
        )

    def validate(self) -> None:
        if not self.bot_token:
            raise RuntimeError("CKNEXUS_TELEGRAM_BOT_TOKEN is required")


class TelegramBridge:
    def __init__(self, config: TelegramBridgeConfig, request_json: JsonRequest = _default_json_request):
        config.validate()
        self.config = config
        self.request_json = request_json
        self.offset = 0

    @property
    def telegram_base(self) -> str:
        return f"https://api.telegram.org/bot{self.config.bot_token}"

    def _ck_headers(self) -> dict[str, str]:
        if not self.config.ck_access_token:
            return {}
        return {"Authorization": f"Bearer {self.config.ck_access_token}"}

    def send_message(self, chat_id: int, text: str) -> None:
        self.request_json(
            f"{self.telegram_base}/sendMessage",
            {"chat_id": chat_id, "text": text[:4000]},
            None,
        )

    def _allowed(self, chat_id: int) -> bool:
        return chat_id in self.config.allowed_chat_ids

    def _status_text(self) -> str:
        data = self.request_json(f"{self.config.ck_api_base}/api/status", None, None)
        return (
            "CK-NEXUS STATUS\n"
            f"name={data.get('name')}\n"
            f"version={data.get('version')}\n"
            f"mode={data.get('mode')}\n"
            f"model={data.get('model')}\n"
            f"database_ready={data.get('database_ready')}\n"
            f"access_required={data.get('access_required')}"
        )

    def _ask(self, chat_id: int, prompt: str) -> str:
        if not self.config.ck_access_token:
            return "BLOCKED: CKNEXUS_ACCESS_TOKEN is not configured on the worker."
        payload = {
            "agent_id": self.config.default_agent_id,
            "prompt": prompt,
            "session_id": f"telegram:{chat_id}",
            "audience": "ผู้ใช้ Telegram",
            "platform": "Telegram",
            "tone": "เป็นธรรมชาติ",
            "language": "ไทย",
        }
        result = self.request_json(
            f"{self.config.ck_api_base}/api/runs",
            payload,
            self._ck_headers(),
        )
        return str(result.get("content") or result)

    def handle_message(self, message: dict[str, Any]) -> None:
        chat = message.get("chat") or {}
        chat_id = int(chat.get("id", 0))
        text = str(message.get("text") or "").strip()
        if not chat_id or not text:
            return

        if text.startswith("/whoami"):
            self.send_message(chat_id, f"chat_id={chat_id}\nใช้ค่านี้ใน allowlist บน VPS เท่านั้น")
            return

        if not self._allowed(chat_id):
            self.send_message(chat_id, "BLOCKED: chat นี้ยังไม่ได้รับอนุญาตจาก CK-NEXUS")
            return

        if text.startswith("/start") or text.startswith("/help"):
            self.send_message(chat_id, "/status /health /ask <ข้อความ> /whoami")
        elif text.startswith("/status"):
            self.send_message(chat_id, self._status_text())
        elif text.startswith("/health"):
            self.send_message(chat_id, "CK-NEXUS Telegram bridge=READY\n" + self._status_text())
        elif text.startswith("/ask "):
            prompt = text.removeprefix("/ask ").strip()
            if len(prompt) < 3:
                self.send_message(chat_id, "BLOCKED: prompt สั้นเกินไป")
            else:
                self.send_message(chat_id, self._ask(chat_id, prompt))
        else:
            self.send_message(chat_id, "ใช้ /help เพื่อดูคำสั่งที่อนุญาต")

    def poll_once(self) -> int:
        query = urllib.parse.urlencode({"timeout": 25, "offset": self.offset})
        data = self.request_json(f"{self.telegram_base}/getUpdates?{query}", None, None)
        processed = 0
        for update in data.get("result", []):
            update_id = int(update.get("update_id", 0))
            self.offset = max(self.offset, update_id + 1)
            message = update.get("message")
            if isinstance(message, dict):
                self.handle_message(message)
                processed += 1
        return processed

    def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # pragma: no cover - runtime resilience path
                print(f"telegram_bridge_error={type(exc).__name__}")
                time.sleep(3)


def main() -> None:
    TelegramBridge(TelegramBridgeConfig.from_env()).run_forever()


if __name__ == "__main__":
    main()
