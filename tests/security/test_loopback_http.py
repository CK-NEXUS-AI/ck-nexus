import urllib.request

import pytest

from scripts._safe_http import _LoopbackRedirect, require_loopback_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/health",
        "https://127.0.0.1:9443/health",
        "http://[::1]:8000/health",
    ],
)
def test_require_loopback_url_accepts_loopback_ip_literals(url):
    assert require_loopback_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/health",
        "http://10.0.0.5:8000/health",
        "http://localhost:8000/health",
        "http://127.0.0.1@evil.example/health",
        "file:///etc/passwd",
        "http://127.0.0.1:bad/health",
    ],
)
def test_require_loopback_url_rejects_non_loopback_or_ambiguous_urls(url):
    with pytest.raises(ValueError):
        require_loopback_url(url)


def test_redirect_handler_rejects_redirect_to_remote_host():
    request = urllib.request.Request("http://127.0.0.1:8000/health")
    handler = _LoopbackRedirect()
    with pytest.raises(ValueError):
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/collect")


def test_redirect_handler_rejects_cross_port_loopback_redirect():
    request = urllib.request.Request("http://127.0.0.1:8000/health")
    handler = _LoopbackRedirect()
    with pytest.raises(ValueError):
        handler.redirect_request(request, None, 302, "Found", {}, "http://127.0.0.1:9000/collect")
