"""Global Knowledge Discovery capability for CK-NEXUS.

This package is intentionally network-agnostic. It defines the canonical
contracts, policy gates, and discovery planning needed by crawler/search
adapters without granting those adapters authority over CK-NEXUS state.
"""

from .contracts import (
    Claim,
    DiscoveryMode,
    EntityRef,
    Reliability,
    Relation,
    SearchRequest,
    SourceKind,
    SourceRef,
)
from .planner import DiscoveryPlan, DiscoveryTask, build_discovery_plan
from .policy import CrawlPolicyInput, IngestDecision, evaluate_crawl_policy

__all__ = [
    "Claim",
    "CrawlPolicyInput",
    "DiscoveryMode",
    "DiscoveryPlan",
    "DiscoveryTask",
    "EntityRef",
    "IngestDecision",
    "Reliability",
    "Relation",
    "SearchRequest",
    "SourceKind",
    "SourceRef",
    "build_discovery_plan",
    "evaluate_crawl_policy",
]
