from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
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
                    f'ckn_http_requests_total{{method="{method}",route="{route}",'
                    f'status_class="{status_class}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP ckn_http_request_duration_seconds_sum Aggregate request latency.",
                    "# TYPE ckn_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, route), total in sorted(self._latency_sum.items()):
                lines.append(
                    f'ckn_http_request_duration_seconds_sum{{method="{method}",'
                    f'route="{route}"}} {total:.6f}'
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


_GENAI_ALLOWED_OPERATIONS = {
    "chat",
    "create_agent",
    "embeddings",
    "execute_tool",
    "generate_content",
    "invoke_agent",
    "invoke_workflow",
    "retrieval",
    "text_completion",
}

_GENAI_ALLOWED_EXTRA_ATTRIBUTES = frozenset(
    {
        "gen_ai.response.id",
        "gen_ai.response.model",
        "gen_ai.response.time_to_first_chunk",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.usage.cache_read.input_tokens",
        "gen_ai.usage.cache_creation.input_tokens",
        "gen_ai.usage.reasoning.output_tokens",
        "gen_ai.workflow.name",
        "cknexus.workflow.id",
        "cknexus.node.id",
    }
)


@dataclass(frozen=True, slots=True)
class CKExecutionContext:
    task_id: str
    run_id: str
    correlation_id: str
    causation_id: str | None = None
    agent_id: str | None = None
    tool_id: str | None = None
    evidence_id: str | None = None
    verifier_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenAISpanEnvelope:
    span_name: str
    attributes: dict[str, str | int | float | bool]
    links: dict[str, str]


class OTelGenAIBridge:
    """Build safe exporter-neutral GenAI correlation metadata without exporting it."""

    @staticmethod
    def build_span(
        *,
        operation: str,
        context: CKExecutionContext,
        provider_name: str | None = None,
        request_model: str | None = None,
        response_model: str | None = None,
        extra_attributes: dict[str, str | int | float | bool] | None = None,
    ) -> GenAISpanEnvelope:
        operation = operation.strip()
        if operation not in _GENAI_ALLOWED_OPERATIONS:
            raise ValueError("unsupported_gen_ai_operation")
        if not context.task_id or not context.run_id or not context.correlation_id:
            raise ValueError("ck_execution_identity_incomplete")

        attrs: dict[str, str | int | float | bool] = {
            "gen_ai.operation.name": operation,
            "cknexus.task.id": context.task_id,
            "cknexus.run.id": context.run_id,
            "cknexus.correlation.id": context.correlation_id,
            "cknexus.telemetry.content_recording": False,
        }
        if context.agent_id:
            attrs["cknexus.agent.id"] = context.agent_id
        if context.tool_id:
            attrs["cknexus.tool.id"] = context.tool_id
        if context.verifier_id:
            attrs["cknexus.verifier.id"] = context.verifier_id
        if provider_name:
            attrs["gen_ai.provider.name"] = provider_name
        if request_model:
            attrs["gen_ai.request.model"] = request_model
        if response_model:
            attrs["gen_ai.response.model"] = response_model

        for key, value in (extra_attributes or {}).items():
            if key not in _GENAI_ALLOWED_EXTRA_ATTRIBUTES:
                raise ValueError(f"gen_ai_attribute_not_allowlisted:{key}")
            attrs[key] = value

        links: dict[str, str] = {
            "task": _genai_digest_ref(context.task_id),
            "run": _genai_digest_ref(context.run_id),
            "correlation": _genai_digest_ref(context.correlation_id),
        }
        if context.causation_id:
            links["causation"] = _genai_digest_ref(context.causation_id)
        if context.evidence_id:
            links["evidence"] = _genai_digest_ref(context.evidence_id)

        return GenAISpanEnvelope(
            span_name=f"gen_ai.{operation}",
            attributes=attrs,
            links=links,
        )

    @staticmethod
    def safe_baggage(context: CKExecutionContext) -> dict[str, str]:
        """Return only non-secret CK correlation identifiers suitable for propagation."""
        baggage = {
            "cknexus.task.id": context.task_id,
            "cknexus.run.id": context.run_id,
            "cknexus.correlation.id": context.correlation_id,
        }
        if context.causation_id:
            baggage["cknexus.causation.id"] = context.causation_id
        return baggage


def _genai_digest_ref(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"
