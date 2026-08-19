from __future__ import annotations

import json
from pathlib import Path

from .models import WorkflowPattern


class PatternRegistry:
    def __init__(self, patterns: tuple[WorkflowPattern, ...]) -> None:
        keys = [(p.id, p.version) for p in patterns]
        if len(keys) != len(set(keys)):
            raise ValueError("pattern id/version pairs must be unique")
        self._patterns = {(p.id, p.version): p for p in patterns}

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> PatternRegistry:
        selected = Path(path) if path else Path(__file__).with_name("patterns.json")
        raw = json.loads(selected.read_text(encoding="utf-8"))
        patterns = tuple(WorkflowPattern.from_mapping(item) for item in raw.get("patterns", []))
        if not patterns:
            raise ValueError("pattern registry cannot be empty")
        return cls(patterns)

    def get(self, pattern_id: str, version: str | None = None) -> WorkflowPattern:
        candidates = [p for (pid, _), p in self._patterns.items() if pid == pattern_id]
        if not candidates:
            raise KeyError(pattern_id)
        if version is not None:
            for pattern in candidates:
                if pattern.version == version:
                    return pattern
            raise KeyError(f"{pattern_id}@{version}")
        return sorted(candidates, key=lambda p: p.version)[-1]

    def all(self) -> tuple[WorkflowPattern, ...]:
        return tuple(sorted(self._patterns.values(), key=lambda p: (p.id, p.version)))
