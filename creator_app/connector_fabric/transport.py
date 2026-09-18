from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


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


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, connect_host: str, port: int, **kwargs) -> None:
        super().__init__(host, port, **kwargs)
        self._connect_host = connect_host

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._connect_host, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        connect_host: str,
        port: int,
        *,
        context: ssl.SSLContext,
        **kwargs,
    ) -> None:
        super().__init__(host, port, context=context, **kwargs)
        self._connect_host = connect_host

    def connect(self) -> None:
        raw = socket.create_connection(
            (self._connect_host, self.port), self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


class UrllibHttpTransport:
    """Bounded, TLS-verifying transport that deliberately does not follow redirects."""

    def __init__(self, *, max_response_bytes: int = 2_000_000) -> None:
        self.max_response_bytes = max_response_bytes
        self._tls_context = ssl.create_default_context()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> TransportResponse:
        from urllib.parse import urlsplit

        parsed = urlsplit(url)
        host = parsed.hostname
        if not host or parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("unsupported connector URL")
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        addresses = tuple(
            sorted(
                {
                    result[4][0]
                    for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
                }
            )
        )
        if not addresses:
            raise OSError("connector hostname resolved to no addresses")
        address = ipaddress.ip_address(addresses[0])
        if not address.is_global:
            raise ValueError("connector destination resolved to a non-public address")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        request_headers = dict(headers)
        request_headers.setdefault("Host", parsed.netloc)
        if parsed.scheme.lower() == "https":
            conn = _PinnedHTTPSConnection(
                host, address.compressed, port, timeout=timeout, context=self._tls_context
            )
        else:
            conn = _PinnedHTTPConnection(host, address.compressed, port, timeout=timeout)
        try:
            conn.request(method.upper(), path, body=body, headers=request_headers)
            response = conn.getresponse()
            payload = self._read_bounded(response)
            return TransportResponse(response.status, dict(response.headers.items()), payload)
        finally:
            conn.close()

    def _read_bounded(self, response) -> bytes:  # noqa: ANN001
        payload = response.read(self.max_response_bytes + 1)
        if len(payload) > self.max_response_bytes:
            raise ResponseTooLargeError("Connector response exceeded configured size limit.")
        return payload
