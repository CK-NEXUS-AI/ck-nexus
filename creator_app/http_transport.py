"""Direct HTTP transport helpers with proxy and redirect handling disabled."""

from __future__ import annotations

import ssl
import urllib.request


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so credentials are never forwarded to another origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_direct_request(request: urllib.request.Request, timeout: float):
    """Open an HTTP(S) request directly, ignoring environment proxies and redirects."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirectHandler(),
    )
    return opener.open(request, timeout=timeout)
