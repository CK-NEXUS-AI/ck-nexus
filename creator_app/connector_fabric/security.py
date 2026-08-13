from __future__ import annotations

import base64
import ipaddress
import re
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit


class EndpointSecurityError(ValueError):
    """Endpoint rejected before any network request is made."""


@dataclass(frozen=True, slots=True)
class EndpointPolicy:
    allow_private_network: bool = False
    require_https: bool = True
    max_url_length: int = 2048


Resolver = Callable[[str], Iterable[str]]


def _default_resolver(host: str) -> tuple[str, ...]:
    addresses: set[str] = set()
    for result in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
        addresses.add(result[4][0])
    return tuple(sorted(addresses))


def validate_endpoint(
    url: str,
    *,
    policy: EndpointPolicy | None = None,
    resolver: Resolver = _default_resolver,
) -> tuple[str, ...]:
    policy = policy or EndpointPolicy()
    candidate = url.strip()
    if not candidate or len(candidate) > policy.max_url_length:
        raise EndpointSecurityError("Connector URL is empty or too long.")

    parsed = urlsplit(candidate)
    if parsed.username or parsed.password:
        raise EndpointSecurityError("Credentials are not allowed inside connector URLs.")
    if parsed.fragment:
        raise EndpointSecurityError("Connector URL fragments are not allowed.")
    if parsed.query:
        raise EndpointSecurityError("Connector URL query strings are not allowed; bind credentials through the broker.")
    if not parsed.hostname:
        raise EndpointSecurityError("Connector URL must include a hostname.")
    if (
        policy.require_https
        and parsed.scheme.lower() != "https"
        and not (policy.allow_private_network and parsed.scheme.lower() == "http")
    ):
        raise EndpointSecurityError("Remote connector endpoints must use HTTPS.")
    if parsed.scheme.lower() not in {"https", "http"}:
        raise EndpointSecurityError("Unsupported connector URL scheme.")

    try:
        addresses = tuple(resolver(parsed.hostname))
    except OSError as exc:
        raise EndpointSecurityError("Connector hostname could not be resolved.") from exc
    if not addresses:
        raise EndpointSecurityError("Connector hostname resolved to no addresses.")

    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise EndpointSecurityError("Connector DNS returned an invalid address.") from exc
        if not policy.allow_private_network and not address.is_global:
            raise EndpointSecurityError("Connector endpoint resolves to a non-public address.")
    return addresses


_HEADER_TOKEN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_RESERVED_HEADERS = {
    "authorization",
    "cookie",
    "host",
    "content-length",
    "content-type",
    "connection",
    "proxy-authorization",
    "mcp-protocol-version",
    "mcp-method",
    "mcp-name",
}


def encode_mcp_header_value(value: str) -> str:
    sentinel = value.startswith("=?base64?") and value.endswith("?=")
    plain_ascii = all(0x21 <= ord(ch) <= 0x7E for ch in value)
    if plain_ascii and not sentinel:
        return value
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    return f"=?base64?{encoded}?="


def validate_x_mcp_headers(schema: dict) -> tuple[str, ...]:
    """Return declared x-mcp-header names or raise for unsafe declarations.

    The validator walks statically reachable object properties only and never resolves
    external $ref values. A malformed tool can therefore be excluded while discovery
    continues for other tools.
    """

    found: list[str] = []

    def walk(node: object, depth: int = 0) -> None:
        if depth > 32:
            raise ValueError("schema depth exceeds connector safety limit")
        if isinstance(node, dict):
            header = node.get("x-mcp-header")
            if header is not None:
                if not isinstance(header, str) or not _HEADER_TOKEN.fullmatch(header):
                    raise ValueError("invalid x-mcp-header name")
                if header.lower() in _RESERVED_HEADERS or header.lower().startswith("mcp-param-"):
                    raise ValueError("x-mcp-header uses a reserved header name")
                found.append(header)
            ref = node.get("$ref")
            if isinstance(ref, str) and not ref.startswith("#"):
                raise ValueError("external schema references are not auto-dereferenced")
            properties = node.get("properties")
            if isinstance(properties, dict):
                for child in properties.values():
                    walk(child, depth + 1)
            for keyword in ("allOf", "anyOf", "oneOf"):
                values = node.get(keyword)
                if isinstance(values, list):
                    for child in values:
                        walk(child, depth + 1)
            items = node.get("items")
            if isinstance(items, (dict, list)):
                walk(items, depth + 1)
        elif isinstance(node, list):
            for child in node:
                walk(child, depth + 1)

    walk(schema)
    return tuple(found)
