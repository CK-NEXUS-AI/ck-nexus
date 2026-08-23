import pytest

from creator_app.observability.otel_genai_bridge import CKExecutionContext, OTelGenAIBridge


def _context() -> CKExecutionContext:
    return CKExecutionContext(
        task_id="task-1",
        run_id="run-1",
        correlation_id="corr-1",
        causation_id="cause-1",
        agent_id="agent-1",
        tool_id="tool-1",
        evidence_id="evd-1",
        verifier_id="verifier-1",
    )


def test_bridge_maps_ck_identity_to_genai_metadata_without_content() -> None:
    span = OTelGenAIBridge.build_span(
        operation="execute_tool",
        context=_context(),
        provider_name="openai",
        request_model="example-model",
    )
    assert span.span_name == "gen_ai.execute_tool"
    assert span.attributes["gen_ai.operation.name"] == "execute_tool"
    assert span.attributes["gen_ai.provider.name"] == "openai"
    assert span.attributes["cknexus.task.id"] == "task-1"
    assert span.attributes["cknexus.run.id"] == "run-1"
    assert span.attributes["cknexus.telemetry.content_recording"] is False
    assert span.links["evidence"].startswith("sha256:")


def test_sensitive_content_attributes_are_rejected() -> None:
    with pytest.raises(ValueError, match="gen_ai_attribute_not_allowlisted"):
        OTelGenAIBridge.build_span(
            operation="invoke_agent",
            context=_context(),
            extra_attributes={"gen_ai.input.messages": "secret content"},
        )


def test_arbitrary_genai_body_is_rejected_even_without_sensitive_marker() -> None:
    with pytest.raises(ValueError, match="gen_ai_attribute_not_allowlisted"):
        OTelGenAIBridge.build_span(
            operation="invoke_agent",
            context=_context(),
            extra_attributes={"gen_ai.request.body": "private content"},
        )


def test_unknown_ck_namespace_is_rejected() -> None:
    with pytest.raises(ValueError, match="gen_ai_attribute_not_allowlisted"):
        OTelGenAIBridge.build_span(
            operation="invoke_agent",
            context=_context(),
            extra_attributes={"cknexus.secret.value": "not allowed"},
        )


def test_usage_token_metrics_are_allowed() -> None:
    span = OTelGenAIBridge.build_span(
        operation="chat",
        context=_context(),
        extra_attributes={
            "gen_ai.usage.input_tokens": 10,
            "gen_ai.usage.output_tokens": 4,
        },
    )
    assert span.attributes["gen_ai.usage.input_tokens"] == 10
    assert span.attributes["gen_ai.usage.output_tokens"] == 4


def test_unscoped_attributes_are_rejected() -> None:
    with pytest.raises(ValueError, match="gen_ai_attribute_not_allowlisted"):
        OTelGenAIBridge.build_span(
            operation="invoke_workflow",
            context=_context(),
            extra_attributes={"customer.email": "user@example.test"},
        )


def test_unsupported_operation_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported_gen_ai_operation"):
        OTelGenAIBridge.build_span(operation="arbitrary", context=_context())


def test_safe_baggage_excludes_evidence_verifier_tool_and_provider_data() -> None:
    baggage = OTelGenAIBridge.safe_baggage(_context())
    assert baggage == {
        "cknexus.task.id": "task-1",
        "cknexus.run.id": "run-1",
        "cknexus.correlation.id": "corr-1",
        "cknexus.causation.id": "cause-1",
    }


def test_evidence_links_are_digest_only() -> None:
    span = OTelGenAIBridge.build_span(operation="invoke_agent", context=_context())
    assert "evd-1" not in span.links.values()
    assert span.links["evidence"].startswith("sha256:")
