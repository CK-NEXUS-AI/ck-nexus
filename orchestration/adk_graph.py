"""Optional Google ADK graph execution adapter.

CK-NEXUS remains the governance authority. This module only translates an
already-approved execution plan into a Google ADK v2 Workflow graph.

The ADK dependency is optional at import time so the governance core remains
usable when ADK is not installed.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class AdkGraphUnavailable(RuntimeError):
    """Raised when an ADK graph is requested without google-adk installed."""


def _workflow_class() -> Any:
    try:
        from google.adk import Workflow
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise AdkGraphUnavailable(
            "google-adk is not installed; install the optional 'adk' extra"
        ) from exc
    return Workflow


def build_sequential_workflow(
    name: str,
    nodes: Sequence[Any],
) -> Any:
    """Build a deterministic ADK v2 sequential graph.

    Governance must happen before this function is called. The returned graph
    has no authority to grant permissions, approve side effects, or bypass
    CK-NEXUS verification/evidence controls.
    """
    if not name.strip():
        raise ValueError("workflow name must not be empty")
    if not nodes:
        raise ValueError("workflow requires at least one node")

    Workflow = _workflow_class()
    return Workflow(
        name=name,
        edges=[("START", *tuple(nodes))],
    )
