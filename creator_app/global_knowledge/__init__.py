"""Global Knowledge Discovery capability for CK-NEXUS.

This package is intentionally network-agnostic. It defines the canonical
contracts, policy gates, discovery planning, and deterministic information
filtering needed by crawler/search adapters without granting those adapters
authority over CK-NEXUS state.
"""

from .contracts import (
    Claim,
    DiscoveryMode,
    EntityRef,
    Relation,
    Reliability,
    SearchRequest,
    SourceKind,
    SourceRef,
)
from .filtering import (
    CandidateDecision,
    ExpansionStrategy,
    FilterAction,
    FilterBatchResult,
    FilterCandidate,
    FilterPolicy,
    FilterReason,
    SearchExpansion,
    filter_candidates,
)
from .planner import DiscoveryPlan, DiscoveryTask, build_discovery_plan
from .policy import CrawlPolicyInput, IngestDecision, evaluate_crawl_policy

__all__ = [
    "CandidateDecision",
    "Claim",
    "CrawlPolicyInput",
    "DiscoveryMode",
    "DiscoveryPlan",
    "DiscoveryTask",
    "EntityRef",
    "ExpansionStrategy",
    "FilterAction",
    "FilterBatchResult",
    "FilterCandidate",
    "FilterPolicy",
    "FilterReason",
    "IngestDecision",
    "Reliability",
    "Relation",
    "SearchExpansion",
    "SearchRequest",
    "SourceKind",
    "SourceRef",
    "build_discovery_plan",
    "evaluate_crawl_policy",
    "filter_candidates",
]
