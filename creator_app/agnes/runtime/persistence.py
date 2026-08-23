from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

from .durable import DurableCheckpoint


class DurableCheckpointStore(Protocol):
    def save(self, checkpoint: DurableCheckpoint) -> str: ...
    def load(self, run_id: str) -> DurableCheckpoint | None: ...


def _checkpoint_payload(checkpoint: DurableCheckpoint) -> dict[str, Any]:
    return {
        "run_id": checkpoint.run_id,
        "step_index": checkpoint.step_index,
        "state": checkpoint.state,
        "digest": checkpoint.digest,
        "parent_digest": checkpoint.parent_digest,
        "pending_writes": checkpoint.pending_writes,
    }


@dataclass(slots=True)
class JsonFileCheckpointStore:
    """Small local durable store for development/edge recovery tests.

    This is not a production database. Writes are atomic via replace(), and
    loaded checkpoints are always digest-verified before being returned.
    """

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        safe = hashlib.sha256(run_id.encode()).hexdigest()
        return self.root / f"{safe}.json"

    def save(self, checkpoint: DurableCheckpoint) -> str:
        if not checkpoint.verify():
            raise ValueError("refusing to persist invalid checkpoint")
        path = self._path(checkpoint.run_id)
        tmp = path.with_suffix(".tmp")
        raw = json.dumps(_checkpoint_payload(checkpoint), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        tmp.write_text(raw, encoding="utf-8")
        tmp.replace(path)
        return hashlib.sha256(raw.encode()).hexdigest()

    def load(self, run_id: str) -> DurableCheckpoint | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        checkpoint = DurableCheckpoint(
            run_id=payload["run_id"],
            step_index=int(payload["step_index"]),
            state=dict(payload["state"]),
            digest=payload["digest"],
            parent_digest=payload.get("parent_digest"),
            pending_writes=dict(payload.get("pending_writes") or {}),
        )
        if checkpoint.run_id != run_id:
            raise ValueError("checkpoint store run_id mismatch")
        if not checkpoint.verify():
            raise ValueError("persisted checkpoint digest mismatch")
        return checkpoint
