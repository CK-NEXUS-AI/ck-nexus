"""Deterministic multilingual discovery planning.

The planner creates work items only. Execution remains behind CK-NEXUS
authorization, connector, rate-limit, and evidence gates.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import DiscoveryMode, SearchRequest, SourceKind

_DEFAULT_SOURCE_PRIORITY = (
    SourceKind.GOVERNMENT,
    SourceKind.ACADEMIC,
    SourceKind.STRUCTURED_DATA,
    SourceKind.PUBLIC_DOCUMENT,
    SourceKind.NEWS,
    SourceKind.INDUSTRY,
    SourceKind.WIKI,
    SourceKind.COMMUNITY,
    SourceKind.SOCIAL,
)


@dataclass(frozen=True, slots=True)
class DiscoveryTask:
    task_id: str
    query: str
    mode: DiscoveryMode
    language: str
    region: str
    source_kind: SourceKind
    priority: int
    require_original_language: bool


@dataclass(frozen=True, slots=True)
class DiscoveryPlan:
    query: str
    tasks: tuple[DiscoveryTask, ...]
    max_sources: int
    freshness_seconds: int | None


def build_discovery_plan(request: SearchRequest) -> DiscoveryPlan:
    source_kinds = request.source_kinds or _DEFAULT_SOURCE_PRIORITY
    tasks: list[DiscoveryTask] = []

    ordinal = 0
    for region in request.regions:
        for language in request.languages:
            for source_kind in source_kinds:
                ordinal += 1
                tasks.append(
                    DiscoveryTask(
                        task_id=f"discover-{ordinal:04d}",
                        query=request.query,
                        mode=request.mode,
                        language=language,
                        region=region,
                        source_kind=source_kind,
                        priority=ordinal,
                        require_original_language=request.require_original_language,
                    )
                )

    return DiscoveryPlan(
        query=request.query,
        tasks=tuple(tasks),
        max_sources=request.max_sources,
        freshness_seconds=request.freshness_seconds,
    )
