from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping


_ALLOWED_OPERATIONS = {
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

_FORBIDDEN_CONTENT_MARKERS = {
    "prompt",
    "input.messages",
    "output.messages",
    "system_instructions",
    "retrieval.query.text",
    "raw_content",
    "credential",
    "credentials",
    "api_key",
    "authorization",
}


@dataclass(frozen=True)
class CKExecutionContext:
    task_id: str
    run_id: str
    correlation_id: str
    causation_id: str | None = None
    agent_id: str | None = None
    tool_id: str | None = None
    evidence_id: str | None = None
    verifier_id: str | None = None


@dataclass(frozen=True)
class GenAISpanEnvelope:
    span_name: str
    attributes: Mapping[str, str | int | float | bool]
    links: Mapping[str, str]


class OTelGenAIBridge:
    """Exporter-neutral metadata bridge for OpenTelemetry GenAI semantics.

    CK-NEXUS execution/evidence identities remain authoritative. This class only
    creates correlation metadata and never exports telemetry by itself.
    Prompt/output/message content and credentials are intentionally unsupported.
    """

    @staticmethod
    def build_span(
        *,
        operation: str,
        context: CKExecutionContext,
        provider_name: str | None = None,
        request_model: str | None = None,
        response_model: str | None = None,
        extra_attributes: Mapping[str, str | int | float | bool] | None = None,
    ) -> GenAISpanEnvelope:
        operation = operation.strip()
        if operation not in _ALLOWED_OPERATIONS:
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
            lowered = key.lower()
            if any(marker in lowered for marker in _FORBIDDEN_CONTENT_MARKERS):
                raise ValueError(f"sensitive_or_content_attribute_forbidden:{key}")
            if key.startswith("cknexus.") or key.startswith("gen_ai."):
                attrs[key] = value
            else:
                raise ValueError(f"unscoped_attribute_forbidden:{key}")

        links: dict[str, str] = {
            "task": _digest_ref(context.task_id),
            "run": _digest_ref(context.run_id),
            "correlation": _digest_ref(context.correlation_id),
        }
        if context.causation_id:
            links["causation"] = _digest_ref(context.causation_id)
        if context.evidence_id:
            links["evidence"] = _digest_ref(context.evidence_id)

        return GenAISpanEnvelope(
            span_name=f"gen_ai.{operation}",
            attributes=attrs,
            links=links,
        )

    @staticmethod
    def safe_baggage(context: CKExecutionContext) -> Mapping[str, str]:
        """Return only non-secret correlation identifiers suitable for propagation."""
        baggage = {
            "cknexus.task.id": context.task_id,
            "cknexus.run.id": context.run_id,
            "cknexus.correlation.id": context.correlation_id,
        }
        if context.causation_id:
            baggage["cknexus.causation.id"] = context.causation_id
        return baggage


def _digest_ref(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"
