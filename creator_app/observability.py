from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4

CORRELATION_HEADER = "X-Correlation-ID"
_SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def correlation_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if candidate and _SAFE_CORRELATION.fullmatch(candidate):
        return candidate
    return f"ck_{uuid4().hex}"


def redact(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(
                token in lowered
                for token in (
                    "token",
                    "secret",
                    "password",
                    "api_key",
                    "authorization",
                    "cookie",
                    "credential",
                )
            ):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class StructuredLogger:
    def __init__(self, name: str = "cknexus.observability") -> None:
        self._logger = logging.getLogger(name)

    def emit(self, event: str, **fields: object) -> None:
        payload = {"event": event, **redact(fields)}
        self._logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class RequestObservation:
    method: str
    route: str
    status_code: int
    duration_seconds: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, str], int] = defaultdict(int)
        self._latency_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._errors: dict[tuple[str, str], int] = defaultdict(int)
        self._started = time.monotonic()

    def observe(self, observation: RequestObservation) -> None:
        status_class = f"{observation.status_code // 100}xx"
        key = (observation.method, observation.route, status_class)
        latency_key = (observation.method, observation.route)
        with self._lock:
            self._requests[key] += 1
            self._latency_sum[latency_key] += max(0.0, observation.duration_seconds)
            if observation.status_code >= 500:
                self._errors[latency_key] += 1

    def render_prometheus(self) -> list[str]:
        with self._lock:
            lines = [
                "# HELP ckn_process_uptime_seconds Process uptime.",
                "# TYPE ckn_process_uptime_seconds gauge",
                f"ckn_process_uptime_seconds {max(0.0, time.monotonic() - self._started):.6f}",
                "# HELP ckn_http_requests_total HTTP requests by method, route and status class.",
                "# TYPE ckn_http_requests_total counter",
            ]
            for (method, route, status_class), count in sorted(self._requests.items()):
                lines.append(
                    f'ckn_http_requests_total{{method="{method}",route="{route}",status_class="{status_class}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP ckn_http_request_duration_seconds_sum Aggregate request latency.",
                    "# TYPE ckn_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, route), total in sorted(self._latency_sum.items()):
                lines.append(
                    f'ckn_http_request_duration_seconds_sum{{method="{method}",route="{route}"}} {total:.6f}'
                )
            lines.extend(
                [
                    "# HELP ckn_http_5xx_total HTTP server errors.",
                    "# TYPE ckn_http_5xx_total counter",
                ]
            )
            for (method, route), count in sorted(self._errors.items()):
                lines.append(f'ckn_http_5xx_total{{method="{method}",route="{route}"}} {count}')
            return lines
