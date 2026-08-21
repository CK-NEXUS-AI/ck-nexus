"""AGNES cognitive foundation primitives.

These modules are advisory and orchestration-oriented. They never grant execution
authority, credentials, approvals, or production readiness.
"""

from .blackboard import BlackboardEntry, BlackboardEntryType, CognitiveBlackboard
from .capabilities import CapabilityFamily, CapabilityRegistry, default_capability_registry
from .feedback import FeedbackController, FeedbackObservation, FeedbackSignal
from .meta_reasoner import (
    CompositionPlan,
    ExecutionPrimitive,
    IntelligenceNeed,
    MetaReasoner,
    TaskProfile,
)
from .progress import ProgressIntelligence, ProgressState, ProgressTransition

__all__ = [
    "BlackboardEntry",
    "BlackboardEntryType",
    "CapabilityFamily",
    "CapabilityRegistry",
    "CognitiveBlackboard",
    "CompositionPlan",
    "ExecutionPrimitive",
    "FeedbackController",
    "FeedbackObservation",
    "FeedbackSignal",
    "IntelligenceNeed",
    "MetaReasoner",
    "ProgressIntelligence",
    "ProgressState",
    "ProgressTransition",
    "TaskProfile",
    "default_capability_registry",
]
