"""Context compiler for selecting minimal sufficient task context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextItem:
    item_id: str
    kind: str
    content: str
    priority: int = 0
    trusted: bool = True
    stale: bool = False
    token_cost: int = 0


@dataclass(frozen=True, slots=True)
class CompiledContext:
    items: tuple[ContextItem, ...]
    total_token_cost: int
    dropped_ids: tuple[str, ...]


class ContextCompiler:
    """Select trusted, non-stale context under a deterministic budget."""

    def compile(self, items: list[ContextItem], token_budget: int) -> CompiledContext:
        if token_budget < 0:
            raise ValueError("token_budget must be non-negative")

        candidates = [item for item in items if item.trusted and not item.stale]
        candidates.sort(key=lambda item: (-item.priority, item.token_cost, item.item_id))

        selected: list[ContextItem] = []
        dropped: list[str] = []
        used = 0
        for item in candidates:
            cost = max(0, item.token_cost)
            if used + cost <= token_budget:
                selected.append(item)
                used += cost
            else:
                dropped.append(item.item_id)

        excluded = {item.item_id for item in items if not item.trusted or item.stale}
        dropped.extend(sorted(excluded))
        return CompiledContext(tuple(selected), used, tuple(dropped))
