from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from creator_app.agnes_ledger import AppendOnlyLedger

from .manifest import ImmutableExecutionManifest
from .result import SkillExecutionResult

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+=*", re.I),
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        redacted = value
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("<redacted>", redacted)
        return redacted
    return value


@dataclass(slots=True)
class EvidenceBuilder:
    ledger: AppendOnlyLedger

    def pre_audit(self, manifest: ImmutableExecutionManifest) -> str:
        row = self.ledger.append("execution_pre_audit", manifest.as_dict())
        return str(row["hash"])

    def finalize(
        self,
        manifest: ImmutableExecutionManifest,
        result: SkillExecutionResult,
    ) -> str:
        payload = {
            "manifest_hash": manifest.manifest_hash,
            "execution_id": manifest.execution_id,
            "skill_id": manifest.skill_id,
            "status": result.status.value,
            "output": redact(result.output),
            "artifacts": list(result.artifacts),
            "error": redact(result.error),
            "duration_ms": result.duration_ms,
        }
        row = self.ledger.append("execution_final_audit", payload)
        return str(row["hash"])
