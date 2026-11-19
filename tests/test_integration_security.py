from __future__ import annotations

from urllib.request import Request

import pytest

from creator_app.github_integration import GitHubIntegration
from creator_app.integration_security import (
    UntrustedIntegrationUrl,
    open_trusted_request,
    validate_trusted_https_url,
)
from creator_app.integrations import GoogleDriveIntegration, SlackIntegration


@pytest.mark.parametrize(
    ("url", "hosts"),
    [
        ("https://slack.com/api/auth.test", {"slack.com"}),
        ("https://www.googleapis.com/drive/v3/about?fields=user", {"www.googleapis.com"}),
        ("https://api.github.com/user", {"api.github.com"}),
    ],
)
def test_default_provider_urls_are_trusted(url: str, hosts: set[str]):
    assert validate_trusted_https_url(url, trusted_hosts=hosts) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.github.com/user",
        "https://api.github.com.evil.example/user",
        "https://api.github.com@evil.example/user",
        "https://user:password@api.github.com/user",
    ],
)
def test_untrusted_or_unsafe_provider_urls_are_rejected(url: str):
    with pytest.raises(UntrustedIntegrationUrl):
        validate_trusted_https_url(url, trusted_hosts={"api.github.com"})


def test_custom_provider_host_requires_explicit_allowlist():
    with pytest.raises(UntrustedIntegrationUrl):
        SlackIntegration("secret", api_base="https://slack.enterprise.example/api")

    integration = SlackIntegration(
        "secret",
        api_base="https://slack.enterprise.example/api",
        trusted_hosts={"slack.enterprise.example"},
    )
    assert integration.api_base == "https://slack.enterprise.example/api"


def test_github_enterprise_host_requires_explicit_allowlist():
    with pytest.raises(UntrustedIntegrationUrl):
        GitHubIntegration("secret", api_base="https://github.enterprise.example/api/v3")

    integration = GitHubIntegration(
        "secret",
        api_base="https://github.enterprise.example/api/v3",
        trusted_hosts={"github.enterprise.example"},
    )
    assert integration.api_base == "https://github.enterprise.example/api/v3"


def test_google_custom_host_requires_explicit_allowlist():
    with pytest.raises(UntrustedIntegrationUrl):
        GoogleDriveIntegration("secret", api_base="https://google-proxy.example/drive/v3")


def test_request_is_rejected_before_transport_for_untrusted_host(monkeypatch):
    called = False

    class FailIfOpened:
        def open(self, *args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("transport must not receive an untrusted request")

    monkeypatch.setattr(
        "creator_app.integration_security.build_opener", lambda *args: FailIfOpened()
    )
    request = Request(
        "https://evil.example/steal",
        headers={"Authorization": "Bearer should-never-leave-process"},
    )

    with pytest.raises(UntrustedIntegrationUrl):
        open_trusted_request(request, trusted_hosts={"api.github.com"}, timeout=1)
    assert called is False
