from __future__ import annotations

import ssl
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class ResponseTooLargeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> TransportResponse: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class UrllibHttpTransport:
    """Bounded, TLS-verifying transport that deliberately does not follow redirects."""

    def __init__(self, *, max_response_bytes: int = 2_000_000) -> None:
        self.max_response_bytes = max_response_bytes
        context = ssl.create_default_context()
        self._opener = build_opener(_NoRedirect(), HTTPSHandler(context=context))

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> TransportResponse:
        request = Request(url=url, data=body, headers=dict(headers), method=method.upper())
        try:
            with self._opener.open(request, timeout=timeout) as response:
                payload = self._read_bounded(response)
                return TransportResponse(response.status, dict(response.headers.items()), payload)
        except HTTPError as exc:
            payload = self._read_bounded(exc)
            return TransportResponse(exc.code, dict(exc.headers.items()), payload)

    def _read_bounded(self, response) -> bytes:  # noqa: ANN001
        payload = response.read(self.max_response_bytes + 1)
        if len(payload) > self.max_response_bytes:
            raise ResponseTooLargeError("Connector response exceeded configured size limit.")
        return payload
