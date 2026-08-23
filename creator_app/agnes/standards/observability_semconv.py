from __future__ import annotations

from typing import Mapping, Any


def build_genai_span_attributes(
    *,
    operation_name: str,
    provider_name: str | None,
    model_name: str | None,
    ck_run_id: str,
    ck_evidence_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
    tool_type: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a privacy-minimal OpenTelemetry GenAI attribute set.

    Raw prompts, raw tool arguments, secrets and full provider payloads are excluded
    by design. CK identifiers remain first-class correlation keys.
    """

    attrs: dict[str, Any] = {
        "gen_ai.operation.name": operation_name,
        "ck.run.id": ck_run_id,
    }
    if provider_name:
        attrs["gen_ai.provider.name"] = provider_name
    if model_name:
        attrs["gen_ai.request.model"] = model_name
    if ck_evidence_id:
        attrs["ck.evidence.id"] = ck_evidence_id
    if input_tokens is not None:
        attrs["gen_ai.usage.input_tokens"] = input_tokens
    if output_tokens is not None:
        attrs["gen_ai.usage.output_tokens"] = output_tokens
    if cache_read_input_tokens is not None:
        attrs["gen_ai.usage.cache_read.input_tokens"] = cache_read_input_tokens
    if cache_creation_input_tokens is not None:
        attrs["gen_ai.usage.cache_creation.input_tokens"] = cache_creation_input_tokens
    if tool_type:
        attrs["gen_ai.tool.type"] = tool_type
    if extra:
        for key, value in extra.items():
            if key.startswith("gen_ai.") or key.startswith("ck."):
                attrs[key] = value
    return attrs
