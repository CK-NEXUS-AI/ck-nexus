from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class UntrustedIntegrationUrl(ValueError):
    """Raised before credentials can be sent to an untrusted integration host."""


def normalize_trusted_hosts(hosts: Iterable[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for raw_host in hosts:
        host = raw_host.strip().lower().rstrip(".")
        if not host or "://" in host or "/" in host or "@" in host:
            raise ValueError("Trusted hosts must be host names, not URLs.")
        normalized.add(host)
    if not normalized:
        raise ValueError("At least one trusted integration host is required.")
    return frozenset(normalized)


def validate_trusted_https_url(url: str, *, trusted_hosts: Iterable[str]) -> str:
    """Validate an outbound credential-bearing URL against an exact host allowlist."""

    if not url or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
        raise UntrustedIntegrationUrl("Integration URL is empty or contains invalid whitespace.")

    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise UntrustedIntegrationUrl("Credential-bearing integration URLs must use HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise UntrustedIntegrationUrl("Integration URLs must not contain user information.")
    if parsed.fragment:
        raise UntrustedIntegrationUrl("Integration URLs must not contain fragments.")

    host = (parsed.hostname or "").lower().rstrip(".")
    allowed = normalize_trusted_hosts(trusted_hosts)
    if not host or host not in allowed:
        raise UntrustedIntegrationUrl("Integration host is not in the trusted-host allowlist.")
    return url


def validate_trusted_https_base_url(url: str, *, trusted_hosts: Iterable[str]) -> str:
    validate_trusted_https_url(url, trusted_hosts=trusted_hosts)
    parsed = urlsplit(url)
    if parsed.query:
        raise UntrustedIntegrationUrl("Integration base URLs must not contain a query string.")
    return url.rstrip("/")


class _NoCredentialRedirectHandler(HTTPRedirectHandler):
    """Never forward a credential-bearing request through an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def open_trusted_request(
    request: Request,
    *,
    trusted_hosts: Iterable[str],
    timeout: int,
):
    """Open a pre-validated request without following redirects that could leak headers."""

    validate_trusted_https_url(request.full_url, trusted_hosts=trusted_hosts)
    opener = build_opener(_NoCredentialRedirectHandler())
    return opener.open(request, timeout=timeout)
