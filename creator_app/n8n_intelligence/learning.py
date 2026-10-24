"""Bounded, evidence-only feedback context for future Auto Developer tasks."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

_SAFE_PATH_PREFIXES = ("creator_app/", "tests/", "docs/")
_SAFE_REASON = re.compile(r"[^a-zA-Z0-9_:-]+")


class AgentLearningMemory:
    """Summarize outcomes, not prompts or model output, for safer iterative work."""

    def __init__(self, evidence_dir: str | Path, *, max_records: int = 20) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.max_records = max(1, min(int(max_records), 50))

    def context_for(self, task: str) -> str:
        del task  # Task text is untrusted and is never stored or echoed into memory.
        if not self.evidence_dir.is_dir():
            return "No prior verified outcomes are available yet."
        paths = sorted(
            self.evidence_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[: self.max_records]
        records: list[dict[str, Any]] = []
        for path in paths:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("state"), str):
                records.append(value)
        if not records:
            return "No prior verified outcomes are available yet."

        verified = [
            item
            for item in records
            if item.get("state") == "verified" and item.get("tests_ok") is True
        ]
        failed = [
            item for item in records if item.get("state") not in {"verified", "skipped", "idle"}
        ]
        blockers = Counter(
            self._reason(item.get("reason") or item.get("gitops_reason") or item.get("state"))
            for item in failed
        )
        blockers = Counter({key: count for key, count in blockers.items() if key})
        changed_paths = Counter(
            path
            for item in verified
            for path in item.get("changed_paths", [])
            if isinstance(path, str) and path.startswith(_SAFE_PATH_PREFIXES) and len(path) <= 160
        )
        lines = [
            f"Historical evidence (latest {len(records)} records):",
            f"- verified outcomes: {len(verified)}",
            f"- failed outcomes: {len(failed)}",
        ]
        repeated = [(reason, count) for reason, count in blockers.most_common(4) if count > 1]
        if repeated:
            lines.append(
                "- repeated blockers: "
                + ", ".join(f"{reason} ({count})" for reason, count in repeated)
            )
        recent_paths = [path for path, _ in changed_paths.most_common(5)]
        if recent_paths:
            lines.append("- paths in verified changes: " + ", ".join(recent_paths))
        lines.append(
            "Use this history only as a hint; inspect current code and rerun current tests."
        )
        return "\n".join(lines)[:2400]

    @staticmethod
    def _reason(value: object) -> str:
        reason = _SAFE_REASON.sub("_", str(value or "unknown")).strip("_:")
        return reason[:80]
