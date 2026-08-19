"""Fail-closed discovery and routing for external development assistants.

The fabric intentionally does not install packages, execute shell commands, or
forward secrets. It only discovers already-installed executables and builds a
routing plan. Execution stays behind CK-NEXUS policy/sandbox/evidence gates.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict
from shutil import which
from typing import Any

from .registry import AssistantSpec, active_assistants

WhichFunction = Callable[[str], str | None]


class DevAssistantFabric:
    """Discover and rank approved development assistants without executing them."""

    def __init__(self, path_lookup: WhichFunction = which) -> None:
        self._path_lookup = path_lookup

    def discover(self) -> list[dict[str, Any]]:
        """Return active assistants with redacted local availability metadata."""
        discovered: list[dict[str, Any]] = []
        for spec in active_assistants():
            executable = self._first_available_command(spec)
            discovered.append(
                {
                    "assistant_id": spec.assistant_id,
                    "name": spec.name,
                    "available": executable is not None,
                    "command": executable,
                    "capabilities": sorted(spec.capabilities),
                    "free_entry_path": spec.free_entry_path,
                    "inference_may_cost": spec.inference_may_cost,
                    "authority": "CK-NEXUS",
                    "external_mutation_authorized": False,
                }
            )
        return discovered

    def select(
        self,
        required_capabilities: Iterable[str],
        *,
        limit: int = 3,
        require_installed: bool = True,
    ) -> list[dict[str, Any]]:
        """Rank assistants for a task using capability overlap and availability."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        required = frozenset(item.strip() for item in required_capabilities if item.strip())
        ranked: list[tuple[int, AssistantSpec, str | None]] = []
        for spec in active_assistants():
            executable = self._first_available_command(spec)
            if require_installed and executable is None:
                continue
            overlap = len(required & spec.capabilities)
            if required and overlap == 0:
                continue
            score = overlap * 100
            score += 20 if executable is not None else 0
            score += 5 if not spec.inference_may_cost else 0
            ranked.append((score, spec, executable))

        ranked.sort(key=lambda row: (-row[0], row[1].assistant_id))
        return [
            {
                "assistant_id": spec.assistant_id,
                "name": spec.name,
                "score": score,
                "available": executable is not None,
                "command": executable,
                "matched_capabilities": sorted(required & spec.capabilities),
                "external_mutation_authorized": False,
            }
            for score, spec, executable in ranked[:limit]
        ]

    def build_parallel_plan(
        self,
        task: str,
        workstreams: dict[str, Iterable[str]],
    ) -> dict[str, Any]:
        """Build a non-executing multi-assistant plan for independent workstreams."""
        clean_task = task.strip()
        if not clean_task:
            raise ValueError("task must not be empty")
        streams: list[dict[str, Any]] = []
        for name, capabilities in workstreams.items():
            stream_name = name.strip()
            if not stream_name:
                raise ValueError("workstream names must not be empty")
            candidates = self.select(capabilities, limit=3, require_installed=False)
            streams.append(
                {
                    "name": stream_name,
                    "candidates": candidates,
                    "execution_state": "PLANNED_NOT_EXECUTED",
                }
            )
        return {
            "task": clean_task,
            "authority": "CK-NEXUS",
            "production_status": "NO-GO",
            "release_evidence": False,
            "external_mutation_authorized": False,
            "workstreams": streams,
        }

    @staticmethod
    def catalog() -> list[dict[str, Any]]:
        """Return serializable active registry metadata without local paths."""
        catalog: list[dict[str, Any]] = []
        for spec in active_assistants():
            row = asdict(spec)
            row["status"] = spec.status.value
            row["capabilities"] = sorted(spec.capabilities)
            row["commands"] = list(spec.commands)
            catalog.append(row)
        return catalog

    def _first_available_command(self, spec: AssistantSpec) -> str | None:
        for command in spec.commands:
            if self._path_lookup(command):
                return command
        return None
