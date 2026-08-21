from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .capabilities import CapabilityFamily, CapabilityRegistry


class ExecutionPrimitive(StrEnum):
    RULE = "rule"
    STATISTICAL_MODEL = "statistical_model"
    FOUNDATION_MODEL = "foundation_model"
    WORKFLOW = "workflow"
    AGENT = "agent"
    MULTI_AGENT = "multi_agent"
    HUMAN = "human"
    STOP = "stop"


class IntelligenceNeed(StrEnum):
    DETERMINISTIC = "deterministic"
    PREDICTIVE = "predictive"
    GENERATIVE = "generative"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
    OPEN_ENDED = "open_ended"
    HIGH_RISK = "high_risk"


@dataclass(frozen=True, slots=True)
class TaskProfile:
    goal: str
    needs: frozenset[IntelligenceNeed]
    requires_external_action: bool = False
    requires_long_running_state: bool = False
    requires_human_judgment: bool = False
    deterministic_path_available: bool = False


@dataclass(frozen=True, slots=True)
class CompositionPlan:
    primitive: ExecutionPrimitive
    capability_families: tuple[CapabilityFamily, ...]
    requires_governor: bool
    requires_verification: bool
    requires_human_approval: bool
    rationale: tuple[str, ...]


class MetaReasoner:
    """Deterministic advisory planner for selecting intelligence primitives.

    It selects a composition plan but does not execute, authorize, approve or mutate
    external systems. CK-NEXUS Governor remains the authority boundary.
    """

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def compose(self, task: TaskProfile) -> CompositionPlan:
        if not task.goal.strip():
            raise ValueError("task goal is required")

        families: list[CapabilityFamily] = []
        rationale: list[str] = []
        needs = task.needs

        if task.requires_human_judgment:
            primitive = ExecutionPrimitive.HUMAN
            rationale.append("human judgment is explicitly required")
        elif IntelligenceNeed.HIGH_RISK in needs and not task.deterministic_path_available:
            primitive = ExecutionPrimitive.HUMAN
            rationale.append("high-risk task has no deterministic bounded path")
        elif task.deterministic_path_available and IntelligenceNeed.OPEN_ENDED not in needs:
            primitive = ExecutionPrimitive.WORKFLOW
            families.extend((CapabilityFamily.RULE_BASED, CapabilityFamily.WORKFLOW))
            rationale.append("bounded deterministic workflow is available")
        elif IntelligenceNeed.PREDICTIVE in needs and len(needs) == 1:
            primitive = ExecutionPrimitive.STATISTICAL_MODEL
            families.append(CapabilityFamily.PREDICTIVE)
            rationale.append("prediction is the only requested intelligence need")
        elif IntelligenceNeed.OPEN_ENDED in needs:
            primitive = ExecutionPrimitive.AGENT
            families.extend((CapabilityFamily.AGENTIC, CapabilityFamily.REASONING))
            rationale.append("open-ended goal requires agentic planning")
        elif IntelligenceNeed.REASONING in needs:
            primitive = ExecutionPrimitive.FOUNDATION_MODEL
            families.append(CapabilityFamily.REASONING)
            rationale.append("reasoning is required without open-ended autonomy")
        elif IntelligenceNeed.GENERATIVE in needs:
            primitive = ExecutionPrimitive.FOUNDATION_MODEL
            families.append(CapabilityFamily.GENERATIVE)
            rationale.append("generative output is required")
        else:
            primitive = ExecutionPrimitive.RULE
            families.append(CapabilityFamily.RULE_BASED)
            rationale.append("defaulting to the least-agentic deterministic primitive")

        if IntelligenceNeed.MULTIMODAL in needs:
            families.extend((CapabilityFamily.MULTIMODAL, CapabilityFamily.PERCEPTION))
            rationale.append("multimodal perception is required")
        if task.requires_long_running_state:
            families.extend((CapabilityFamily.DURABLE_AUTONOMOUS, CapabilityFamily.MEMORY))
            rationale.append("long-running state requires durable memory/checkpointing")
        if task.requires_external_action:
            families.extend((CapabilityFamily.GOVERNED, CapabilityFamily.VERIFICATION))
            rationale.append("external action requires governance and verification")

        unique_families = tuple(dict.fromkeys(families))
        for family in unique_families:
            if not self._registry.supports(family):
                raise ValueError(f"required capability is not registered: {family}")

        human_approval = task.requires_human_judgment or (
            task.requires_external_action and IntelligenceNeed.HIGH_RISK in needs
        )
        return CompositionPlan(
            primitive=primitive,
            capability_families=unique_families,
            requires_governor=task.requires_external_action or bool(unique_families),
            requires_verification=task.requires_external_action
            or primitive in {ExecutionPrimitive.AGENT, ExecutionPrimitive.MULTI_AGENT},
            requires_human_approval=human_approval,
            rationale=tuple(rationale),
        )
