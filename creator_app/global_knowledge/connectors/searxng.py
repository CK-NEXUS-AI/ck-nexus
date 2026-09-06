"""SearXNG discovery adapter.

The adapter uses SearXNG only for URL/source discovery. It does not treat
search results as verified evidence and performs no write action.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit


class SearxngStatus(StrEnum):
    SUCCESS = "success"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True, slots=True)
class SearxngConfig:
    base_url: str
    timeout_seconds: float = 10.0
    max_results: int = 20
    safe_search: int = 1

    def __post_init__(self) -> None:
        parts = urlsplit(self.base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("SearXNG base_url must be http(s)")
        if parts.username or parts.password:
            raise ValueError("SearXNG base_url must not contain userinfo")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results must be within 1..100")
        if self.safe_search not in {0, 1, 2}:
            raise ValueError("safe_search must be 0, 1, or 2")


@dataclass(frozen=True, slots=True)
class SearchHit:
    url: str
    title: str
    snippet: str
    engine: str | None = None
    score: float | None = None


@dataclass(frozen=True, slots=True)
class SearxngSearchResult:
    status: SearxngStatus
    hits: tuple[SearchHit, ...]
    reason: str | None = None


class SearxngDiscoveryAdapter:
    def __init__(
        self,
        config: SearxngConfig,
        *,
        fetch_json=None,
    ) -> None:
        self.config = config
        self._fetch_json = fetch_json

    async def search(
        self,
        query: str,
        *,
        language: str | None = None,
        categories: tuple[str, ...] = ("general",),
        time_range: str | None = None,
    ) -> SearxngSearchResult:
        normalized = query.strip()
        if not normalized:
            raise ValueError("query is required")
        if len(normalized) > 1000:
            raise ValueError("query must be <= 1000 characters")
        if time_range not in {None, "day", "month", "year"}:
            raise ValueError("time_range must be day, month, year, or None")

        params: dict[str, str | int] = {
            "q": normalized,
            "format": "json",
            "safesearch": self.config.safe_search,
        }
        if language:
            params["language"] = language
        if categories:
            params["categories"] = ",".join(categories)
        if time_range:
            params["time_range"] = time_range

        endpoint = urljoin(self.config.base_url.rstrip("/") + "/", "search")
        url = f"{endpoint}?{urlencode(params)}"

        try:
            payload = await self._load_json(url)
        except Exception as exc:
            return SearxngSearchResult(
                status=SearxngStatus.PROVIDER_ERROR,
                hits=(),
                reason=f"provider_error:{type(exc).__name__}",
            )

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return SearxngSearchResult(
                status=SearxngStatus.INVALID_RESPONSE,
                hits=(),
                reason="results_array_missing",
            )

        hits: list[SearchHit] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            result_url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if not _public_result_url_shape(result_url):
                continue
            score = _optional_float(item.get("score"))
            hits.append(
                SearchHit(
                    url=result_url,
                    title=title,
                    snippet=str(item.get("content") or "").strip(),
                    engine=_optional_text(item.get("engine")),
                    score=score,
                )
            )
            if len(hits) >= self.config.max_results:
                break

        return SearxngSearchResult(
            status=SearxngStatus.SUCCESS,
            hits=tuple(hits),
        )

    async def _load_json(self, url: str) -> dict[str, Any]:
        if self._fetch_json is not None:
            value = self._fetch_json(url)
            if hasattr(value, "__await__"):
                value = await value
            if not isinstance(value, dict):
                raise TypeError("fetch_json must return a mapping")
            return value

        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx gateway extra is required") from exc

        headers = {
            "Accept": "application/json",
            "User-Agent": "CK-NEXUS-Research/1.0",
        }
        if _is_loopback_base_url(self.config.base_url):
            headers["X-Real-IP"] = "127.0.0.1"

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=False,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type.lower():
                raise ValueError("SearXNG JSON format is not enabled")
            payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("SearXNG response must be an object")
        return payload


def _is_loopback_base_url(value: str) -> bool:
    hostname = urlsplit(value).hostname
    if hostname == "localhost":
        return True
    if hostname is None:
        return False
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _public_result_url_shape(value: str) -> bool:
    parts = urlsplit(value)
    return (
        parts.scheme in {"http", "https"}
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
