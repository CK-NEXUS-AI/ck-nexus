from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
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
    """Local development checkpoint store with atomic replace + fsync.

    This adapter is for development/edge validation only. Production durability
    still requires an independently verified external state backend.
    """

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        safe = hashlib.sha256(run_id.encode()).hexdigest()
        return self.root / f"{safe}.json"

    def save(self, checkpoint: DurableCheckpoint) -> str:
        if not checkpoint.verify():
            raise ValueError("refusing to persist invalid checkpoint")
        path = self._path(checkpoint.run_id)
        tmp = path.with_suffix(".tmp")
        raw = json.dumps(
            _checkpoint_payload(checkpoint),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
        try:
            directory_fd = os.open(self.root, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
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
