from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RuntimeEvidence:
    evidence_id: str
    correlation_id: str
    source_sha: str
    environment_id: str
    component: str
    action: str
    status: str
    timestamp: datetime
    refs: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
