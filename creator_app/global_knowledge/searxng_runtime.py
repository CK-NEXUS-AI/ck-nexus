"""SearXNG development-runtime readiness checks.

The runtime checker is intentionally restricted to loopback HTTP endpoints.
It proves transport and JSON readiness only; it does not verify search-result
correctness or evidence quality.
"""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit


@dataclass(frozen=True, slots=True)
class DoctorResult:
    ok: bool
    reason: str
    result_count: int = 0


def validate_local_base_url(base_url: str) -> tuple[str, int]:
    parts = urlsplit(base_url)
    if parts.scheme != "http":
        raise ValueError("SearXNG doctor requires local http")
    if parts.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("SearXNG doctor only permits loopback targets")
    if parts.username or parts.password:
        raise ValueError("SearXNG base URL must not contain userinfo")
    return parts.hostname, parts.port or 80


def check_json_api(
    base_url: str,
    *,
    query: str = "ck nexus",
    timeout_seconds: float = 5.0,
) -> DoctorResult:
    host, port = validate_local_base_url(base_url)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    params = urlencode(
        {
            "q": query,
            "format": "json",
            "language": "en",
            "categories": "general",
        }
    )
    connection = http.client.HTTPConnection(
        host,
        port,
        timeout=timeout_seconds,
    )
    try:
        connection.request(
            "GET",
            f"/search?{params}",
            headers={
                "Accept": "application/json",
                "User-Agent": "CK-NEXUS-SearXNG-Doctor/1.0",
                "X-Real-IP": "127.0.0.1",
            },
        )
        response = connection.getresponse()
        raw = response.read()
    except OSError as exc:
        return DoctorResult(
            ok=False,
            reason=f"connection_error:{type(exc).__name__}",
        )
    finally:
        connection.close()

    if response.status != 200:
        return DoctorResult(
            ok=False,
            reason=f"http_status_{response.status}",
        )

    content_type = response.getheader("Content-Type", "")
    if "application/json" not in content_type.lower():
        return DoctorResult(
            ok=False,
            reason="json_format_not_enabled",
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return DoctorResult(
            ok=False,
            reason="invalid_json_response",
        )

    if not isinstance(payload, dict):
        return DoctorResult(
            ok=False,
            reason="json_root_not_object",
        )
    results = payload.get("results")
    if not isinstance(results, list):
        return DoctorResult(
            ok=False,
            reason="results_array_missing",
        )

    return DoctorResult(
        ok=True,
        reason="ready",
        result_count=len(results),
    )
