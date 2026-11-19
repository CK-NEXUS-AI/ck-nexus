"""Convert development signals into safe Control Plane queue payloads."""

from __future__ import annotations

import hashlib
from typing import Any

from .analysis import priority_for
from .models import DevelopmentSignal


def build_task(signal: DevelopmentSignal, repeat_count: int) -> tuple[str, dict[str, Any]]:
    priority = priority_for(signal.category, repeat_count)
    digest = hashlib.sha256(f"{signal.event_id}:{signal.execution_id}".encode()).hexdigest()[:20]
    payload: dict[str, Any] = {
        "handler": "n8n_development_signal",
        "node_id": f"n8n-{digest}",
        "task": signal.title,
        "description": signal.description[:2000],
        "priority": priority,
        "source": "n8n",
        "event_id": signal.event_id,
        "execution_id": signal.execution_id,
        "production_status": "NO-GO",
        "external_mutation_authorized": False,
        "release_evidence": False,
        "evidence_refs": [f"n8n://execution/{signal.execution_id}"],
    }
    return f"n8n-{digest}", payload
