from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

from creator_app.connector_fabric.security import (
    EndpointPolicy,
    EndpointSecurityError,
    Resolver,
    validate_endpoint,
)


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
        endpoint_policy: EndpointPolicy | None = None,
    ) -> TransportResponse: ...


ConnectionFactory = Callable[[tuple[str, int], float], socket.socket]


def _default_connection_factory(address: tuple[str, int], timeout: float) -> socket.socket:
    return socket.create_connection(address, timeout=timeout)


def _normalize_ip(raw: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    candidate = raw.split("%", 1)[0]
    address = ipaddress.ip_address(candidate)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _validate_connected_peer(
    peer_ip: str,
    *,
    allowed_addresses: tuple[str, ...],
    policy: EndpointPolicy,
) -> None:
    try:
        peer = _normalize_ip(peer_ip)
        allowed = {_normalize_ip(raw) for raw in allowed_addresses}
    except ValueError as exc:
        raise EndpointSecurityError(
            "Connector transport reported an invalid peer address."
        ) from exc

    if peer not in allowed:
        raise EndpointSecurityError(
            "Connector peer address did not match the address set approved during validation."
        )
    if not policy.allow_private_network and not peer.is_global:
        raise EndpointSecurityError("Connector peer is not a public/global address.")


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        connect_ip: str,
        allowed_addresses: tuple[str, ...],
        policy: EndpointPolicy,
        timeout: float,
        connection_factory: ConnectionFactory,
    ) -> None:
        super().__init__(host=host, port=port, timeout=timeout)
        self._connect_ip = connect_ip
        self._allowed_addresses = allowed_addresses
        self._policy = policy
        self._connection_factory = connection_factory

    def connect(self) -> None:
        sock = self._connection_factory((self._connect_ip, self.port), float(self.timeout))
        try:
            peer_ip = str(sock.getpeername()[0])
            _validate_connected_peer(
                peer_ip,
                allowed_addresses=self._allowed_addresses,
                policy=self._policy,
            )
        except Exception:
            sock.close()
            raise
        self.sock = sock


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        connect_ip: str,
        allowed_addresses: tuple[str, ...],
        policy: EndpointPolicy,
        timeout: float,
        context: ssl.SSLContext,
        connection_factory: ConnectionFactory,
    ) -> None:
        super().__init__(host=host, port=port, timeout=timeout, context=context)
        self._connect_ip = connect_ip
        self._allowed_addresses = allowed_addresses
        self._policy = policy
        self._connection_factory = connection_factory
        self._ssl_context = context

    def connect(self) -> None:
        raw_sock = self._connection_factory((self._connect_ip, self.port), float(self.timeout))
        tls_sock: ssl.SSLSocket | None = None
        try:
            raw_peer = str(raw_sock.getpeername()[0])
            _validate_connected_peer(
                raw_peer,
                allowed_addresses=self._allowed_addresses,
                policy=self._policy,
            )
            tls_sock = self._ssl_context.wrap_socket(raw_sock, server_hostname=self.host)
            tls_peer = str(tls_sock.getpeername()[0])
            _validate_connected_peer(
                tls_peer,
                allowed_addresses=self._allowed_addresses,
                policy=self._policy,
            )
        except Exception:
            if tls_sock is not None:
                tls_sock.close()
            raw_sock.close()
            raise
        self.sock = tls_sock


class UrllibHttpTransport:
    """Peer-bound HTTP transport with TLS hostname verification and no redirects.

    The historical class name is retained for compatibility, but requests no longer
    delegate connection establishment to urllib. The endpoint is resolved exactly at
    the validation boundary, a numeric validated address is selected for the TCP
    connection, and the connected peer is checked before any HTTP headers (including
    credentials) are written. HTTPS still verifies the original hostname through SNI
    and the default certificate-validation context.
    """

    def __init__(
        self,
        *,
        max_response_bytes: int = 2_000_000,
        resolver: Resolver | None = None,
        connection_factory: ConnectionFactory = _default_connection_factory,
    ) -> None:
        self.max_response_bytes = max_response_bytes
        self._resolver = resolver
        self._connection_factory = connection_factory
        self._ssl_context = ssl.create_default_context()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
        endpoint_policy: EndpointPolicy | None = None,
    ) -> TransportResponse:
        policy = endpoint_policy or EndpointPolicy()
        validation_kwargs: dict[str, object] = {"policy": policy}
        if self._resolver is not None:
            validation_kwargs["resolver"] = self._resolver
        allowed_addresses = validate_endpoint(url, **validation_kwargs)  # type: ignore[arg-type]

        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None:
            raise EndpointSecurityError("Connector URL must include a hostname.")
        scheme = parsed.scheme.lower()
        port = parsed.port or (443 if scheme == "https" else 80)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"

        last_error: OSError | ssl.SSLError | http.client.HTTPException | None = None
        for connect_ip in allowed_addresses:
            connection: http.client.HTTPConnection
            if scheme == "https":
                connection = _PinnedHTTPSConnection(
                    host,
                    port,
                    connect_ip=connect_ip,
                    allowed_addresses=allowed_addresses,
                    policy=policy,
                    timeout=timeout,
                    context=self._ssl_context,
                    connection_factory=self._connection_factory,
                )
            else:
                connection = _PinnedHTTPConnection(
                    host,
                    port,
                    connect_ip=connect_ip,
                    allowed_addresses=allowed_addresses,
                    policy=policy,
                    timeout=timeout,
                    connection_factory=self._connection_factory,
                )

            try:
                connection.request(
                    method.upper(),
                    target,
                    body=body,
                    headers=dict(headers),
                )
                response = connection.getresponse()
                payload = self._read_bounded(response)
                return TransportResponse(
                    response.status,
                    dict(response.headers.items()),
                    payload,
                )
            except EndpointSecurityError:
                raise
            except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
                last_error = exc
            finally:
                connection.close()

        if last_error is not None:
            raise last_error
        raise EndpointSecurityError("Connector endpoint had no usable validated address.")

    def _read_bounded(self, response: http.client.HTTPResponse) -> bytes:
        payload = response.read(self.max_response_bytes + 1)
        if len(payload) > self.max_response_bytes:
            raise ResponseTooLargeError("Connector response exceeded configured size limit.")
        return payload
