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


_FAMILIES: tuple[tuple[CapabilityFamily, str, str, str], ...] = (
    (CapabilityFamily.RULE_BASED, "Rule-Based AI", "Deterministic rules and constraints", "low"),
    (CapabilityFamily.PREDICTIVE, "Predictive AI", "Classification, forecasting and anomaly detection", "medium"),
    (CapabilityFamily.GENERATIVE, "Generative AI", "Generate text, media and code", "medium"),
    (CapabilityFamily.REASONING, "Reasoning AI", "Planning, logic and problem solving", "medium"),
    (CapabilityFamily.AGENTIC, "Agentic AI", "Goal-directed tool use", "high"),
    (CapabilityFamily.MULTIMODAL, "Multimodal AI", "Cross-modal understanding", "medium"),
    (CapabilityFamily.CONTEXT, "Context AI", "Select and compact task context", "medium"),
    (CapabilityFamily.MEMORY, "Memory AI", "Persistent knowledge and execution state", "high"),
    (CapabilityFamily.SKILL, "Skill AI", "Portable and composable capability packages", "high"),
    (CapabilityFamily.WORKFLOW, "Workflow AI", "Deterministic and event-driven orchestration", "medium"),
    (CapabilityFamily.COLLABORATIVE, "Collaborative AI", "Council, debate and multi-agent work", "high"),
    (CapabilityFamily.DURABLE_AUTONOMOUS, "Durable Autonomous AI", "Long-running checkpointed work", "high"),
    (CapabilityFamily.PERCEPTION, "Perception AI", "Scene, GUI, temporal and environment understanding", "medium"),
    (CapabilityFamily.WORLD_MODEL, "World-Model AI", "Prediction, simulation and counterfactuals", "high"),
    (CapabilityFamily.EMBODIED, "Embodied AI", "Sensors, actuators and physical-world execution", "critical"),
    (CapabilityFamily.DISCOVERY, "Discovery AI", "Search, experimentation and algorithm discovery", "high"),
    (CapabilityFamily.SCIENTIFIC, "Scientific AI", "Research, experiments and reproducibility", "high"),
    (CapabilityFamily.INTEROPERABILITY, "Interoperability AI", "MCP, A2A and protocol integration", "high"),
    (CapabilityFamily.VERIFICATION, "Verification AI", "Independent result and evidence validation", "high"),
    (CapabilityFamily.GOVERNED, "Governed AI", "Identity, policy, approval and evidence", "critical"),
    (CapabilityFamily.AGENT_USER_INTERACTION, "Agent-User Interaction AI", "Streaming state and human interaction", "medium"),
    (CapabilityFamily.GENERATIVE_INTERFACE, "Generative Interface AI", "Declarative UI intent generation", "medium"),
    (CapabilityFamily.AGENTIC_UI_COMPOSITION, "Agentic UI Composition", "Composable interactive agent interfaces", "medium"),
    (CapabilityFamily.AGENT_NETWORK, "Agent Network AI", "Remote agent discovery and delegation", "high"),
    (CapabilityFamily.AGENT_TRANSACTION_MANDATE, "Agent Mandate AI", "Bounded transaction authority contracts", "critical"),
    (CapabilityFamily.DURABLE_PROTOCOL_TASK, "Durable Protocol Task AI", "Protocol-level durable task state", "high"),
    (CapabilityFamily.INTERACTIVE_ELICITATION, "Interactive Elicitation AI", "Structured human input and secure handoff", "high"),
    (CapabilityFamily.EVALUATION, "Evaluation Intelligence", "Trace, regression, cost and quality evaluation", "medium"),
    (CapabilityFamily.CONTROLLED_SELF_IMPROVEMENT, "Controlled Self-Improvement AI", "Propose and test bounded improvements", "critical"),
    (CapabilityFamily.AGENT_SECURITY, "Agent Security Intelligence", "Trust, poisoning and tool-misuse detection", "critical"),
    (CapabilityFamily.FEEDBACK_CYBERNETIC, "Feedback / Cybernetic AI", "Closed-loop observe-act-measure-correct control", "high"),
    (CapabilityFamily.ORGANIZATIONAL, "Organizational AI", "Roles, authority, dependencies and negotiation", "high"),
    (CapabilityFamily.DELEGATION, "Delegation Intelligence", "Decide what to automate, ask or retain for humans", "high"),
    (CapabilityFamily.USER_MODEL, "User-Model AI", "Transparent, consent-based user modeling", "high"),
    (CapabilityFamily.REFLECTIVE, "Reflective AI", "Observe traces, reframe and propose corrections", "high"),
    (CapabilityFamily.INTENTIONAL, "Intentional AI", "Separate observed state, goals and committed plans", "high"),
    (CapabilityFamily.REACTIVE_REFLEX, "Reactive / Reflex AI", "Immediate deterministic safety responses", "critical"),
    (CapabilityFamily.MIXED_INITIATIVE, "Mixed-Initiative AI", "Human and AI initiative with bounded authority", "high"),
    (CapabilityFamily.ATTENTION, "Attention AI", "Prioritize foreground, peripheral and background signals", "medium"),
    (CapabilityFamily.KNOWLEDGE_ACQUISITION, "Knowledge-Acquisition AI", "Extract, validate and structure expert knowledge", "high"),
)


def default_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        tuple(
            CapabilityDefinition(family=family, name=name, purpose=purpose, default_risk=risk)
            for family, name, purpose, risk in _FAMILIES
        )
    )
