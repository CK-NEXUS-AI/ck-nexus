from __future__ import annotations

import pytest

from creator_app.connector_fabric.security import EndpointPolicy, EndpointSecurityError
from creator_app.connector_fabric.transport import (
    UrllibHttpTransport,
    _PinnedHTTPConnection,
    _validate_connected_peer,
)


def test_transport_uses_validated_numeric_address_without_second_dns_lookup() -> None:
    resolver_calls: list[str] = []
    connection_attempts: list[tuple[str, int]] = []

    def rebinding_resolver(host: str) -> tuple[str, ...]:
        resolver_calls.append(host)
        if len(resolver_calls) == 1:
            return ("93.184.216.34",)
        return ("127.0.0.1",)

    def stop_before_network(address: tuple[str, int], timeout: float):  # noqa: ANN202
        del timeout
        connection_attempts.append(address)
        raise OSError("synthetic connection stop")

    transport = UrllibHttpTransport(
        resolver=rebinding_resolver,
        connection_factory=stop_before_network,
    )

    with pytest.raises(OSError, match="synthetic connection stop"):
        transport.request(
            "GET",
            "https://example.com/mcp",
            headers={"Authorization": "Bearer test-value"},
            body=None,
            timeout=1.0,
        )

    assert resolver_calls == ["example.com"]
    assert connection_attempts == [("93.184.216.34", 443)]


def test_rebound_peer_is_rejected_even_if_initial_address_was_public() -> None:
    with pytest.raises(EndpointSecurityError, match="did not match"):
        _validate_connected_peer(
            "127.0.0.1",
            allowed_addresses=("93.184.216.34",),
            policy=EndpointPolicy(),
        )


def test_credentials_are_not_written_before_peer_binding_passes() -> None:
    class RecordingSocket:
        def __init__(self) -> None:
            self.sent: list[bytes] = []
            self.closed = False

        def getpeername(self) -> tuple[str, int]:
            return ("127.0.0.1", 80)

        def sendall(self, data: bytes) -> None:
            self.sent.append(data)

        def close(self) -> None:
            self.closed = True

    socket_record = RecordingSocket()

    def connection_factory(address: tuple[str, int], timeout: float) -> RecordingSocket:
        assert address == ("93.184.216.34", 80)
        assert timeout == 1.0
        return socket_record

    connection = _PinnedHTTPConnection(
        "example.com",
        80,
        connect_ip="93.184.216.34",
        allowed_addresses=("93.184.216.34",),
        policy=EndpointPolicy(),
        timeout=1.0,
        connection_factory=connection_factory,  # type: ignore[arg-type]
    )
    with pytest.raises(EndpointSecurityError, match="did not match"):
        connection.request(
            "GET",
            "/mcp",
            headers={"Authorization": "Bearer must-not-leak"},
        )

    assert socket_record.sent == []
    assert socket_record.closed is True


def test_explicit_private_network_policy_allows_matching_private_peer() -> None:
    _validate_connected_peer(
        "127.0.0.1",
        allowed_addresses=("127.0.0.1",),
        policy=EndpointPolicy(allow_private_network=True),
    )


def test_ipv4_mapped_ipv6_peer_matches_validated_ipv4_address() -> None:
    _validate_connected_peer(
        "::ffff:93.184.216.34",
        allowed_addresses=("93.184.216.34",),
        policy=EndpointPolicy(),
    )
