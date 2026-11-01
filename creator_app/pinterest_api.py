"""Read-only Pinterest API v5 connector for public board pin metadata."""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.integration_security import open_trusted_request

_BOARD_ID_RE = re.compile(r"^[0-9]{1,20}$")
_API_ROOT = "https://api.pinterest.com/v5"
_IMAGE_HOST = "i.pinimg.com"


class PinterestAPIError(RuntimeError):
    """Sanitized Pinterest API error."""


class PinterestAPIClient:
    """Read public-board Pin metadata using only boards:read and pins:read."""

    def __init__(self, broker: CredentialBroker, *, timeout_seconds: int = 15):
        if not 1 <= timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 1 and 30")
        self.broker = broker
        self.timeout_seconds = timeout_seconds

    def status(self) -> dict[str, object]:
        configured = self.broker.is_configured(
            CredentialId.PINTEREST_ACCESS_TOKEN, consumer="pinterest.api"
        )
        return {
            "provider": "pinterest_api_v5",
            "configured": configured,
            "connected": configured,
            "access_mode": "read_only",
            "required_scopes": ["boards:read", "pins:read"],
            "secret_storage": "credential_broker",
            "image_downloads": False,
            "private_pins_requested": False,
            "write_operations_available": False,
            "bulk_collection_limit": 500,
        }

    def list_board_pins(self, *, board_id: str, limit: int = 500) -> dict[str, object]:
        if not isinstance(board_id, str) or not _BOARD_ID_RE.fullmatch(board_id):
            raise ValueError("board_id must contain only 1-20 digits")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")

        token = self._token()
        records: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        seen_bookmarks: set[str] = set()
        bookmark: str | None = None
        page_count = 0

        while len(records) < limit and page_count < 10:
            page_count += 1
            page_size = min(250, limit - len(records))
            params: dict[str, str | int] = {"page_size": page_size}
            if bookmark:
                params["bookmark"] = bookmark
            url = f"{_API_ROOT}/boards/{quote(board_id, safe='')}/pins?{urlencode(params)}"
            payload = self._get_json(url, token)
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise PinterestAPIError("Pinterest returned an invalid Pins collection.")
            for item in items:
                if not isinstance(item, dict):
                    continue
                pin_id = str(item.get("id") or "").strip()
                if not pin_id or pin_id in seen_ids:
                    continue
                seen_ids.add(pin_id)
                records.append(self._normalize_pin(item, board_id=board_id))
                if len(records) >= limit:
                    break
            next_bookmark = payload.get("bookmark")
            if not isinstance(next_bookmark, str) or not next_bookmark:
                bookmark = None
                break
            if next_bookmark in seen_bookmarks:
                raise PinterestAPIError("Pinterest pagination cursor repeated.")
            seen_bookmarks.add(next_bookmark)
            bookmark = next_bookmark
            if not items:
                break

        return {
            "ok": True,
            "board_id": board_id,
            "items": records,
            "count": len(records),
            "page_count": page_count,
            "limit": limit,
            "more_available": bookmark is not None,
            "next_bookmark": bookmark,
            "rights_status": "unknown",
            "reusable": False,
            "image_bytes_downloaded": 0,
            "write_operations_performed": False,
        }

    def _token(self) -> str:
        try:
            lease = self.broker.acquire(
                CredentialId.PINTEREST_ACCESS_TOKEN,
                consumer="pinterest.api",
            )
            return lease.reveal(consumer="pinterest.api")
        except (ValueError, RuntimeError, PermissionError) as exc:
            raise PinterestAPIError(
                "Pinterest access token is unavailable in the credential broker."
            ) from exc

    def _get_json(self, url: str, token: str) -> dict[str, object]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "CK-NEXUS-Pinterest-ReadOnly",
            },
            method="GET",
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts={"api.pinterest.com"},
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise PinterestAPIError(f"Pinterest API request failed (HTTP {exc.code}).") from None
        except Exception as exc:
            raise PinterestAPIError("Pinterest API request failed safely.") from exc
        if not isinstance(payload, dict):
            raise PinterestAPIError("Pinterest returned an invalid response.")
        return payload

    @staticmethod
    def _normalize_pin(item: dict[str, object], *, board_id: str) -> dict[str, object]:
        media = item.get("media")
        images = media.get("images") if isinstance(media, dict) else None
        image_url = None
        if isinstance(images, dict):
            for size in ("1200x", "600x", "400x300", "150x150"):
                candidate = images.get(size)
                if isinstance(candidate, dict):
                    url = candidate.get("url")
                    if isinstance(url, str) and url.startswith(f"https://{_IMAGE_HOST}/"):
                        image_url = url
                        break
        pin_id = str(item.get("id") or "")
        return {
            "pin_id": pin_id,
            "pin_url": f"https://www.pinterest.com/pin/{pin_id}/",
            "board_id": board_id,
            "title": str(item.get("title") or "")[:500],
            "description": str(item.get("description") or "")[:5000],
            "alt_text": str(item.get("alt_text") or "")[:2000],
            "destination_url": str(item.get("link") or "")[:2000],
            "created_at": str(item.get("created_at") or "")[:64],
            "creative_type": str(item.get("creative_type") or "")[:64],
            "dominant_color": str(item.get("dominant_color") or "")[:16],
            "image_url": image_url,
            "rights_status": "unknown",
            "reusable": False,
        }
