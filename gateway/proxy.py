from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .errors import GatewayError

SENSITIVE_REQUEST_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "host",
    "content-length",
    "connection",
}


@dataclass(frozen=True, slots=True)
class UpstreamResponse:
    status_code: int
    body: bytes
    content_type: str = "application/json"
    headers: dict[str, str] | None = None


class UpstreamClient(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        query: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> UpstreamResponse: ...


class HttpxUpstreamClient:
    async def request(
        self,
        method: str,
        url: str,
        *,
        query: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> UpstreamResponse:
        try:
            import httpx

            safe_headers = {
                key: value
                for key, value in headers.items()
                if key.lower() not in SENSITIVE_REQUEST_HEADERS
            }
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
                response = await client.request(
                    method,
                    url,
                    params=query,
                    content=body,
                    headers=safe_headers,
                )
            return UpstreamResponse(
                status_code=response.status_code,
                body=response.content,
                content_type=response.headers.get("content-type", "application/json"),
                headers={"location": response.headers.get("location", "")}
                if response.is_redirect
                else {},
            )
        except Exception:
            raise GatewayError(
                "UPSTREAM_UNAVAILABLE", "Upstream service is unavailable.", 502, True
            ) from None
