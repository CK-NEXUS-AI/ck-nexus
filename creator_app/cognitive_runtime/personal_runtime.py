"""Integrated privacy-first personal cognitive runtime for CK-NEXUS."""

from __future__ import annotations

from dataclasses import dataclass

from creator_app.ai_gateway import (
    AIGateway,
    DataClass,
    GatewayRequest,
    ModelCapability,
)
from creator_app.conversation_engine import ConversationPlan, plan_response
from creator_app.personal_intelligence import PersonaPreferences
from creator_app.privacy_firewall import (
    ContentEnvelope,
    DataClassification,
    PrivacyPolicy,
    evaluate_disclosure,
)


@dataclass(frozen=True, slots=True)
class CognitiveResponse:
    output: str
    provider_id: str
    model_id: str
    conversation_plan: ConversationPlan
    privacy_evidence: dict[str, object]
    route_evidence: dict[str, object]


_DATA_CLASS_MAP = {
    DataClassification.PUBLIC: DataClass.PUBLIC,
    DataClassification.INTERNAL: DataClass.INTERNAL,
    DataClassification.PERSONAL: DataClass.PERSONAL,
    DataClassification.SENSITIVE: DataClass.SENSITIVE,
    DataClassification.SECRET: DataClass.SENSITIVE,
    DataClassification.REGULATED: DataClass.SENSITIVE,
}


class PersonalCognitiveRuntime:
    """Route minimized data to an eligible model, then normalize response presentation."""

    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    def respond(
        self,
        envelope: ContentEnvelope,
        *,
        required_capabilities: frozenset[ModelCapability],
        privacy_policy: PrivacyPolicy,
        preferences: PersonaPreferences | None = None,
        confidence: float = 1.0,
    ) -> CognitiveResponse:
        data_class = _DATA_CLASS_MAP[envelope.classification]
        routing_request = GatewayRequest(
            prompt=envelope.content,
            required_capabilities=required_capabilities,
            data_class=data_class,
            allow_external=privacy_policy.external_allowed,
            prefer_local=privacy_policy.prefer_local,
        )
        selected = self._gateway.route(routing_request)
        destination = "local" if selected.local else selected.provider_id
        disclosure = evaluate_disclosure(
            envelope,
            destination=destination,
            policy=privacy_policy,
        )
        if not disclosure.allowed:
            raise PermissionError(disclosure.reason)

        prompt = envelope.content if selected.local else disclosure.redacted_content
        invocation_request = GatewayRequest(
            prompt=prompt,
            required_capabilities=required_capabilities,
            data_class=data_class,
            allow_external=not selected.local,
            prefer_local=selected.local,
            allowed_providers=frozenset({selected.provider_id}),
            max_cost_tier=selected.cost_tier,
        )
        response = self._gateway.invoke(invocation_request)
        conversation_plan = plan_response(
            envelope.content,
            preferences=preferences,
            confidence=confidence,
        )
        return CognitiveResponse(
            output=response.output,
            provider_id=response.provider_id,
            model_id=response.model_id,
            conversation_plan=conversation_plan,
            privacy_evidence=disclosure.evidence,
            route_evidence=response.route_evidence,
        )
