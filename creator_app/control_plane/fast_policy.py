"""Deterministic fast-path decisions for known CK-NEXUS failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FastDecision:
    handled: bool
    action_id: str | None
    reason: str


_KNOWN_SIGNALS: tuple[tuple[str, str], ...] = (
    ("cknexus-mcp.service inactive", "restart_cknexus_mcp"),
    ("ck-sentinel container_not_running", "restart_ck_sentinel"),
    ("ck-ops container_not_running", "restart_ck_ops"),
)


def decide_fast(signal: str) -> FastDecision:
    """Map only exact known failure signatures to predefined action IDs."""
    normalized = signal.strip().lower()
    for signature, action_id in _KNOWN_SIGNALS:
        if signature in normalized:
            return FastDecision(True, action_id, f"known failure: {signature}")
    return FastDecision(False, None, "unknown failure; escalate to diagnosis")
