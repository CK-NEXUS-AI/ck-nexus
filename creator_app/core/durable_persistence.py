from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

from .durable_runtime import Checkpoint, DurableTask


class DurableRecord(BaseModel):
    record_type: str
    subject: str
    payload: dict[str, object]


class JsonlDurableStore:
    """Append-only local development store for durable task metadata.

    This is not production storage. It deliberately stores references/digests only;
    raw credentials and opaque resume secrets must remain outside this file.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def _append(self, record: DurableRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = record.model_dump_json() + "\n"
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def append_checkpoint(self, checkpoint: Checkpoint) -> None:
        self._append(
            DurableRecord(
                record_type="checkpoint",
                subject=checkpoint.subject,
                payload=checkpoint.model_dump(mode="json"),
            )
        )

    def append_task(self, task: DurableTask) -> None:
        payload = task.model_dump(mode="json")
        if payload.get("resume_token_ref") and not str(payload["resume_token_ref"]).startswith(
            "credential-ref:"
        ):
            raise ValueError("resume_token_ref must be a credential-ref, never a raw secret")
        self._append(
            DurableRecord(record_type="task", subject=task.subject, payload=payload)
        )

    def read_all(self) -> list[DurableRecord]:
        if not self.path.exists():
            return []
        records: list[DurableRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(DurableRecord.model_validate(json.loads(line)))
        return records
