from __future__ import annotations

import re

from .models import PatternSelection
from .registry import PatternRegistry

_TOKEN = re.compile(r"[a-z0-9_+-]+", re.I)
HIGH_RISK_TAGS = frozenset({"release", "deploy", "credential", "security", "staging"})


class PatternSelector:
    def __init__(self, registry: PatternRegistry) -> None:
        self.registry = registry

    def select(self, text: str, *, intent_tags: tuple[str, ...] = ()) -> PatternSelection:
        tokens = {token.lower() for token in _TOKEN.findall(text)} | {
            item.lower() for item in intent_tags
        }
        ranked: list[tuple[float, object, tuple[str, ...]]] = []
        for pattern in self.registry.all():
            matches = tuple(sorted(tokens & set(pattern.intent_tags)))
            if not matches:
                continue
            risk_bonus = 0.25 if HIGH_RISK_TAGS & set(matches) else 0.0
            confidence = min(0.99, 0.45 + 0.12 * len(matches) + risk_bonus)
            ranked.append((confidence, pattern, matches))
        if not ranked:
            return PatternSelection(None, None, 0.0, ("no deterministic match",), True)
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        confidence, pattern, reasons = ranked[0]
        requires_human = pattern.approval_policy != "none_for_read_only"
        return PatternSelection(pattern.id, pattern.version, confidence, reasons, requires_human)
