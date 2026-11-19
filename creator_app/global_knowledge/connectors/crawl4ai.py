"""Governed optional Crawl4AI adapter.

The adapter enforces CK-NEXUS crawl policy before invoking Crawl4AI. The
dependency is loaded lazily so the default CK-NEXUS installation remains
dependency-light.
"""

from __future__ import annotations

import hashlib
import inspect
import ipaddress
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from ..policy import CrawlPolicyInput, evaluate_crawl_policy


class CrawlStatus(StrEnum):
    SUCCESS = "success"
    BLOCKED_POLICY = "blocked_policy"
    INVALID_URL = "invalid_url"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True, slots=True)
class CrawlRequest:
    url: str
    max_content_chars: int = 500_000

    def __post_init__(self) -> None:
        if self.max_content_chars < 1:
            raise ValueError("max_content_chars must be positive")


@dataclass(frozen=True, slots=True)
class CrawlResult:
    status: CrawlStatus
    url: str
    final_url: str | None = None
    markdown: str = ""
    content_hash: str | None = None
    truncated: bool = False
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class _ProviderPayload:
    success: bool
    markdown: str
    final_url: str | None = None
    error: str | None = None


class Crawl4AIAdapter:
    def __init__(self, *, runner=None) -> None:
        self._runner = runner

    async def crawl(
        self,
        request: CrawlRequest,
        policy_input: CrawlPolicyInput,
    ) -> CrawlResult:
        policy = evaluate_crawl_policy(policy_input)
        if not policy.allowed:
            return CrawlResult(
                status=CrawlStatus.BLOCKED_POLICY,
                url=request.url,
                reason=";".join(policy.reasons),
            )

        if not _safe_http_url_shape(request.url):
            return CrawlResult(
                status=CrawlStatus.INVALID_URL,
                url=request.url,
                reason="url_not_allowed",
            )

        try:
            payload = await self._run(request.url)
        except ImportError:
            return CrawlResult(
                status=CrawlStatus.PROVIDER_UNAVAILABLE,
                url=request.url,
                reason="crawl4ai_not_installed",
            )
        except Exception as exc:
            return CrawlResult(
                status=CrawlStatus.PROVIDER_ERROR,
                url=request.url,
                reason=f"provider_error:{type(exc).__name__}",
            )

        if not payload.success:
            return CrawlResult(
                status=CrawlStatus.PROVIDER_ERROR,
                url=request.url,
                final_url=payload.final_url,
                reason=payload.error or "crawl_failed",
            )

        final_url = payload.final_url or request.url
        if not _safe_http_url_shape(final_url):
            return CrawlResult(
                status=CrawlStatus.INVALID_URL,
                url=request.url,
                final_url=final_url,
                reason="redirect_target_not_allowed",
            )

        markdown = payload.markdown
        truncated = len(markdown) > request.max_content_chars
        bounded = markdown[: request.max_content_chars]
        digest = hashlib.sha256(bounded.encode("utf-8")).hexdigest()

        return CrawlResult(
            status=CrawlStatus.SUCCESS,
            url=request.url,
            final_url=final_url,
            markdown=bounded,
            content_hash=digest,
            truncated=truncated,
        )

    async def _run(self, url: str) -> _ProviderPayload:
        if self._runner is not None:
            value = self._runner(url)
            if inspect.isawaitable(value):
                value = await value
            if isinstance(value, _ProviderPayload):
                return value
            if isinstance(value, dict):
                return _ProviderPayload(
                    success=bool(value.get("success")),
                    markdown=str(value.get("markdown") or ""),
                    final_url=_optional_text(value.get("final_url")),
                    error=_optional_text(value.get("error")),
                )
            raise TypeError("runner must return provider payload")

        return await _run_crawl4ai(url)


async def _run_crawl4ai(url: str) -> _ProviderPayload:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    markdown = getattr(result, "markdown", "")
    if not isinstance(markdown, str):
        markdown = str(markdown or "")

    return _ProviderPayload(
        success=bool(getattr(result, "success", False)),
        markdown=markdown,
        final_url=_optional_text(
            getattr(result, "redirected_url", None)
            or getattr(result, "url", None)
        ),
        error=_optional_text(getattr(result, "error_message", None)),
    )


def _safe_http_url_shape(value: str) -> bool:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False

    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        return True

    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
