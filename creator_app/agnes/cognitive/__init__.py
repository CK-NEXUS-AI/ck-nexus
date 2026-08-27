"""AGNES cognitive foundation primitives.

These modules are advisory and orchestration-oriented. They never grant execution
authority, credentials, approvals, or production readiness.
"""

from .authzen import (
    AUTHZEN_ACCESS_EVALUATION_PATH,
    AUTHZEN_SPEC_VERSION,
    AuthZENAdapter,
    AuthZENEnforcementResult,
)
from .blackboard import BlackboardEntry, BlackboardEntryType, CognitiveBlackboard
from .capabilities import CapabilityFamily, CapabilityRegistry, default_capability_registry
from .context import CompiledContext, ContextCompiler, ContextItem
from .feedback import FeedbackController, FeedbackObservation, FeedbackSignal
from .governor import (
    ActionProposal,
    CognitiveGovernor,
    GovernanceResult,
    GovernorDecision,
    RiskLevel,
)
from .memory import MemoryRecord, TemporalMemory
from .meta_reasoner import (
    CompositionPlan,
    ExecutionPrimitive,
    IntelligenceNeed,
    MetaReasoner,
    TaskProfile,
)
from .progress import ProgressIntelligence, ProgressState, ProgressTransition
from .security import TrustEngine, TrustRecord, TrustState
from .tasks import DurableTask, DurableTaskRuntime, TaskState
from .verification import PassEngine, PassResult, VerificationEvidence, VerificationSubject

__all__ = [
    "AUTHZEN_ACCESS_EVALUATION_PATH",
    "AUTHZEN_SPEC_VERSION",
    "ActionProposal",
    "AuthZENAdapter",
    "AuthZENEnforcementResult",
    "BlackboardEntry",
    "BlackboardEntryType",
    "CapabilityFamily",
    "CapabilityRegistry",
    "CognitiveBlackboard",
    "CognitiveGovernor",
    "CompiledContext",
    "CompositionPlan",
    "ContextCompiler",
    "ContextItem",
    "DurableTask",
    "DurableTaskRuntime",
    "ExecutionPrimitive",
    "FeedbackController",
    "FeedbackObservation",
    "FeedbackSignal",
    "GovernanceResult",
    "GovernorDecision",
    "IntelligenceNeed",
    "MemoryRecord",
    "MetaReasoner",
    "PassEngine",
    "PassResult",
    "ProgressIntelligence",
    "ProgressState",
    "ProgressTransition",
    "RiskLevel",
    "TaskProfile",
    "TaskState",
    "TemporalMemory",
    "TrustEngine",
    "TrustRecord",
    "TrustState",
    "VerificationEvidence",
    "VerificationSubject",
    "default_capability_registry",
]
