"""Restricted read-only n8n API client."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class N8NReadError(RuntimeError):
    pass


class N8NReadClient:
    def __init__(
        self, base_url: str, key_file: Path, timeout: float = 10.0, max_items: int = 50
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be http or https")
        if timeout <= 0 or max_items < 1 or max_items > 50:
            raise ValueError("invalid client bounds")
        self.base_url = base_url.rstrip("/")
        self.key_file = Path(key_file)
        self.timeout = timeout
        self.max_items = max_items

    def list_executions(
        self, cursor: str | None = None
    ) -> tuple[list[dict[str, object]], str | None]:
        try:
            key = self.key_file.read_text().strip()
        except OSError as exc:
            raise N8NReadError("authentication configuration unavailable") from exc
        if not key:
            raise N8NReadError("authentication configuration unavailable")
        params = {"limit": str(self.max_items)}
        if cursor:
            if len(cursor) > 512 or any(char in cursor for char in "\r\n"):
                raise N8NReadError("invalid cursor")
            params["cursor"] = cursor
        url = f"{self.base_url}/executions?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "X-N8N-API-KEY": key,
                "Accept": "application/json",
                "User-Agent": "CK-NEXUS-N8N-Intelligence/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise N8NReadError("n8n response exceeds safe size")
            data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise N8NReadError(f"n8n HTTP error {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise N8NReadError("n8n transport failure") from exc
        except json.JSONDecodeError as exc:
            raise N8NReadError("n8n returned invalid JSON") from exc
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise N8NReadError("n8n response schema invalid")
        rows = [item for item in data["data"] if isinstance(item, dict)]
        if len(rows) > self.max_items:
            raise N8NReadError("n8n returned too many executions")
        next_cursor = data.get("nextCursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise N8NReadError("n8n cursor schema invalid")
        return rows, next_cursor
