"""Scheme-validated urlopen for internal gate/check scripts."""
import ipaddress
import os
import re
import urllib.request
from urllib.parse import urlsplit

_ALLOWED = {"http", "https"}


def _check(url):
    scheme = urlsplit(str(url)).scheme.lower()
    if scheme not in _ALLOWED:
        raise ValueError(f"unsupported URL scheme: {scheme or '(none)'}")


class _SchemeCheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SchemeCheckedRedirect)


def safe_urlopen(req, timeout):
    _check(req.full_url if hasattr(req, "full_url") else req)
    return _OPENER.open(req, timeout=timeout)  # nosec B310 - scheme checked on request and every redirect


def loopback_api_base_url() -> str:
    """Build the internal API URL from a numeric port; callers cannot choose a host."""
    raw_port = os.getenv("CKNEXUS_API_PORT", "8000")
    if not re.fullmatch(r"[0-9]{1,5}", raw_port):
        raise ValueError("CKNEXUS_API_PORT must be a valid TCP port")
    port = int(raw_port)
    if not 1 <= port <= 65535:
        raise ValueError("CKNEXUS_API_PORT must be between 1 and 65535")
    return f"http://127.0.0.1:{port}"


def _check_loopback(url):
    parsed = urlsplit(str(url))
    host = (parsed.hostname or "").lower().rstrip(".")
    try:
        is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "localhost"
    if (
        parsed.scheme.lower() not in _ALLOWED
        or not is_loopback
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("internal HTTP target must be an explicit loopback URL")


class _LoopbackRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_loopback(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_LOOPBACK_OPENER = urllib.request.build_opener(_LoopbackRedirect)


def safe_loopback_urlopen(req, timeout):
    """Open only loopback HTTP(S), including every redirect hop."""
    _check_loopback(req.full_url if hasattr(req, "full_url") else req)
    return _LOOPBACK_OPENER.open(req, timeout=timeout)
