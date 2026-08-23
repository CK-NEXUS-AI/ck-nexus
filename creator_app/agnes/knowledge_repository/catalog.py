from __future__ import annotations

from collections.abc import Iterable

from .models import KnowledgeItem


class KnowledgeCatalog:
    def __init__(self, items: Iterable[KnowledgeItem] = ()) -> None:
        self._items: dict[str, KnowledgeItem] = {item.item_id: item for item in items}

    def add(self, item: KnowledgeItem) -> None:
        self._items[item.item_id] = item

    def get(self, item_id: str) -> KnowledgeItem | None:
        return self._items.get(item_id)

    def all(self) -> tuple[KnowledgeItem, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.item_id))

    def search(self, query: str) -> tuple[KnowledgeItem, ...]:
        terms = {term.casefold() for term in query.split() if term.strip()}
        if not terms:
            return ()

        scored: list[tuple[int, KnowledgeItem]] = []
        for item in self._items.values():
            haystack = " ".join(
                [
                    item.name,
                    item.category,
                    item.summary,
                    item.usage,
                    *item.capabilities,
                    *item.relevance,
                    *item.tags,
                ]
            ).casefold()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].item_id))
        return tuple(item for _, item in scored)
