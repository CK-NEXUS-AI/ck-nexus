from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ConnectorEvidenceLedger:
    """Append-only hash-chained JSONL ledger containing no raw credentials."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()
        self._previous_hash = self._load_last_hash()

    def append(self, event: str, connector_id: str, details: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "connectorId": connector_id,
                "details": details,
                "previousHash": self._previous_hash,
            }
            entry_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
            record = {**payload, "entryHash": entry_hash}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._previous_hash = entry_hash
            return record

    def _load_last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = ""
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        if not last:
            return "0" * 64
        try:
            return str(json.loads(last)["entryHash"])
        except (KeyError, ValueError, TypeError):
            raise RuntimeError("Connector evidence ledger is corrupt.") from None
