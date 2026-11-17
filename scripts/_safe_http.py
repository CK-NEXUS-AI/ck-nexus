"""Loopback-only urlopen for internal gate/check scripts."""

from __future__ import annotations

import ipaddress
import urllib.request
from urllib.parse import urlsplit

_ALLOWED = {"http", "https"}


def require_loopback_url(url: str) -> str:
    """Reject remote hosts before an internal script sends credentials or data."""
    try:
        parsed = urlsplit(str(url))
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        _port = parsed.port  # Force validation of malformed port values.
    except ValueError as exc:
        raise ValueError("malformed URL") from exc
    if scheme not in _ALLOWED:
        raise ValueError(f"unsupported URL scheme: {scheme or '(none)'}")
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials and must include a host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError as exc:
        raise ValueError("URL host must be a loopback IP literal") from exc
    if not address.is_loopback:
        raise ValueError("URL host must be a loopback IP literal")
    return str(url)


class _LoopbackRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_loopback_url(newurl)
        original = urlsplit(req.full_url)
        redirected = urlsplit(newurl)
        if (original.scheme, original.hostname, original.port) != (
            redirected.scheme,
            redirected.hostname,
            redirected.port,
        ):
            raise ValueError("cross-origin redirects are not allowed")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_LoopbackRedirect)


def safe_urlopen(req, timeout):
    url = req.full_url if hasattr(req, "full_url") else req
    require_loopback_url(url)
    return _OPENER.open(req, timeout=timeout)
