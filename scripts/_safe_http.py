"""Scheme-validated urlopen for internal gate/check scripts."""
import urllib.request


def safe_urlopen(req, timeout):
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"unsupported URL scheme: {url.split(':', 1)[0]}")
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310 - scheme validated above
