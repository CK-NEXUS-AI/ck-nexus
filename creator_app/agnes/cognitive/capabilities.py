from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityFamily(StrEnum):
    RULE_BASED = "rule_based"
    PREDICTIVE = "predictive"
    GENERATIVE = "generative"
    REASONING = "reasoning"
    AGENTIC = "agentic"
    MULTIMODAL = "multimodal"
    CONTEXT = "context"
    MEMORY = "memory"
    SKILL = "skill"
    WORKFLOW = "workflow"
    COLLABORATIVE = "collaborative"
    DURABLE_AUTONOMOUS = "durable_autonomous"
    PERCEPTION = "perception"
    WORLD_MODEL = "world_model"
    EMBODIED = "embodied"
    DISCOVERY = "discovery"
    SCIENTIFIC = "scientific"
    INTEROPERABILITY = "interoperability"
    VERIFICATION = "verification"
    GOVERNED = "governed"
    AGENT_USER_INTERACTION = "agent_user_interaction"
    GENERATIVE_INTERFACE = "generative_interface"
    AGENTIC_UI_COMPOSITION = "agentic_ui_composition"
    AGENT_NETWORK = "agent_network"
    AGENT_TRANSACTION_MANDATE = "agent_transaction_mandate"
    DURABLE_PROTOCOL_TASK = "durable_protocol_task"
    INTERACTIVE_ELICITATION = "interactive_elicitation"
    EVALUATION = "evaluation"
    CONTROLLED_SELF_IMPROVEMENT = "controlled_self_improvement"
    AGENT_SECURITY = "agent_security"
    FEEDBACK_CYBERNETIC = "feedback_cybernetic"
    ORGANIZATIONAL = "organizational"
    DELEGATION = "delegation"
    USER_MODEL = "user_model"
    REFLECTIVE = "reflective"
    INTENTIONAL = "intentional"
    REACTIVE_REFLEX = "reactive_reflex"
    MIXED_INITIATIVE = "mixed_initiative"
    ATTENTION = "attention"
    KNOWLEDGE_ACQUISITION = "knowledge_acquisition"


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    family: CapabilityFamily
    name: str
    purpose: str
    default_risk: str
    requires_governor: bool = True


class CapabilityRegistry:
    def __init__(self, definitions: tuple[CapabilityDefinition, ...]) -> None:
        self._by_family = {item.family: item for item in definitions}
        if len(self._by_family) != len(definitions):
            raise ValueError("duplicate capability family")

    def get(self, family: CapabilityFamily) -> CapabilityDefinition:
        return self._by_family[family]

    def all(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(self._by_family.values())

    def supports(self, family: CapabilityFamily) -> bool:
        return family in self._by_family


def _cap(
    family: CapabilityFamily,
    name: str,
    purpose: str,
    risk: str,
) -> tuple[CapabilityFamily, str, str, str]:
    return family, name, purpose, risk


_FAMILIES: tuple[tuple[CapabilityFamily, str, str, str], ...] = (
    _cap(CapabilityFamily.RULE_BASED, "Rule-Based AI", "Rules and constraints", "low"),
    _cap(CapabilityFamily.PREDICTIVE, "Predictive AI", "Prediction and anomalies", "medium"),
    _cap(CapabilityFamily.GENERATIVE, "Generative AI", "Generate text, media and code", "medium"),
    _cap(CapabilityFamily.REASONING, "Reasoning AI", "Planning and logic", "medium"),
    _cap(CapabilityFamily.AGENTIC, "Agentic AI", "Goal-directed tool use", "high"),
    _cap(CapabilityFamily.MULTIMODAL, "Multimodal AI", "Cross-modal understanding", "medium"),
    _cap(CapabilityFamily.CONTEXT, "Context AI", "Select and compact task context", "medium"),
    _cap(CapabilityFamily.MEMORY, "Memory AI", "Knowledge and execution state", "high"),
    _cap(CapabilityFamily.SKILL, "Skill AI", "Portable capability packages", "high"),
    _cap(CapabilityFamily.WORKFLOW, "Workflow AI", "Deterministic orchestration", "medium"),
    _cap(CapabilityFamily.COLLABORATIVE, "Collaborative AI", "Council and agents", "high"),
    _cap(
        CapabilityFamily.DURABLE_AUTONOMOUS,
        "Durable Autonomous AI",
        "Long-running checkpointed work",
        "high",
    ),
    _cap(CapabilityFamily.PERCEPTION, "Perception AI", "Scene understanding", "medium"),
    _cap(CapabilityFamily.WORLD_MODEL, "World-Model AI", "Simulation and counterfactuals", "high"),
    _cap(CapabilityFamily.EMBODIED, "Embodied AI", "Physical-world execution", "critical"),
    _cap(CapabilityFamily.DISCOVERY, "Discovery AI", "Search and experimentation", "high"),
    _cap(CapabilityFamily.SCIENTIFIC, "Scientific AI", "Research and reproducibility", "high"),
    _cap(CapabilityFamily.INTEROPERABILITY, "Interoperability AI", "Protocol integration", "high"),
    _cap(CapabilityFamily.VERIFICATION, "Verification AI", "Independent validation", "high"),
    _cap(CapabilityFamily.GOVERNED, "Governed AI", "Policy, approval and evidence", "critical"),
    _cap(
        CapabilityFamily.AGENT_USER_INTERACTION,
        "Agent-User Interaction AI",
        "Streaming state and human interaction",
        "medium",
    ),
    _cap(
        CapabilityFamily.GENERATIVE_INTERFACE,
        "Generative Interface AI",
        "Declarative UI intent generation",
        "medium",
    ),
    _cap(
        CapabilityFamily.AGENTIC_UI_COMPOSITION,
        "Agentic UI Composition",
        "Composable agent interfaces",
        "medium",
    ),
    _cap(CapabilityFamily.AGENT_NETWORK, "Agent Network AI", "Remote agent delegation", "high"),
    _cap(
        CapabilityFamily.AGENT_TRANSACTION_MANDATE,
        "Agent Mandate AI",
        "Bounded transaction authority",
        "critical",
    ),
    _cap(
        CapabilityFamily.DURABLE_PROTOCOL_TASK,
        "Durable Protocol Task AI",
        "Protocol-level durable task state",
        "high",
    ),
    _cap(
        CapabilityFamily.INTERACTIVE_ELICITATION,
        "Interactive Elicitation AI",
        "Structured human input and secure handoff",
        "high",
    ),
    _cap(CapabilityFamily.EVALUATION, "Evaluation Intelligence", "Trace evaluation", "medium"),
    _cap(
        CapabilityFamily.CONTROLLED_SELF_IMPROVEMENT,
        "Controlled Self-Improvement AI",
        "Propose and test bounded improvements",
        "critical",
    ),
    _cap(
        CapabilityFamily.AGENT_SECURITY,
        "Agent Security Intelligence",
        "Trust and tool-misuse detection",
        "critical",
    ),
    _cap(
        CapabilityFamily.FEEDBACK_CYBERNETIC,
        "Feedback / Cybernetic AI",
        "Closed-loop observe-act-measure-correct control",
        "high",
    ),
    _cap(CapabilityFamily.ORGANIZATIONAL, "Organizational AI", "Roles and dependencies", "high"),
    _cap(CapabilityFamily.DELEGATION, "Delegation Intelligence", "Bounded delegation", "high"),
    _cap(CapabilityFamily.USER_MODEL, "User-Model AI", "Consent-based user modeling", "high"),
    _cap(CapabilityFamily.REFLECTIVE, "Reflective AI", "Trace reflection and correction", "high"),
    _cap(CapabilityFamily.INTENTIONAL, "Intentional AI", "Goals and committed plans", "high"),
    _cap(
        CapabilityFamily.REACTIVE_REFLEX,
        "Reactive / Reflex AI",
        "Deterministic safety responses",
        "critical",
    ),
    _cap(CapabilityFamily.MIXED_INITIATIVE, "Mixed-Initiative AI", "Shared initiative", "high"),
    _cap(CapabilityFamily.ATTENTION, "Attention AI", "Signal prioritization", "medium"),
    _cap(
        CapabilityFamily.KNOWLEDGE_ACQUISITION,
        "Knowledge-Acquisition AI",
        "Extract and validate expert knowledge",
        "high",
    ),
)


def default_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        tuple(
            CapabilityDefinition(
                family=family,
                name=name,
                purpose=purpose,
                default_risk=risk,
            )
            for family, name, purpose, risk in _FAMILIES
        )
    )
