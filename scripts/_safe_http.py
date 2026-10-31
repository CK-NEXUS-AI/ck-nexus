"""Scheme-validated urlopen for internal gate/check scripts."""
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
