from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class LedgerVerification:
    valid: bool
    entries: int
    last_hash: str | None
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "entries": self.entries,
            "last_hash": self.last_hash,
            "error": self.error,
        }


class AppendOnlyLedger:
    """Hash-chained JSONL ledger. It only appends; it has no delete/update API."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _digest(record_without_hash: dict[str, Any]) -> str:
        payload = json.dumps(
            record_without_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state = self.verify()
        if not state.valid:
            raise RuntimeError(f"append-only ledger integrity check failed: {state.error}")
        base = {
            "sequence": state.entries + 1,
            "at": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
            "previous_hash": state.last_hash,
        }
        record = {**base, "hash": self._digest(base)}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def verify(self) -> LedgerVerification:
        if not self.path.exists():
            return LedgerVerification(True, 0, None)
        previous_hash: str | None = None
        count = 0
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for count, line in enumerate(handle, start=1):
                    record = json.loads(line)
                    if record.get("sequence") != count:
                        return LedgerVerification(
                            False, count - 1, previous_hash, "sequence mismatch"
                        )
                    if record.get("previous_hash") != previous_hash:
                        return LedgerVerification(
                            False, count - 1, previous_hash, "hash chain mismatch"
                        )
                    claimed = str(record.get("hash") or "")
                    base = {key: value for key, value in record.items() if key != "hash"}
                    if not claimed or claimed != self._digest(base):
                        return LedgerVerification(
                            False, count - 1, previous_hash, "record digest mismatch"
                        )
                    previous_hash = claimed
        except (OSError, json.JSONDecodeError) as exc:
            return LedgerVerification(False, max(count - 1, 0), previous_hash, type(exc).__name__)
        return LedgerVerification(True, count, previous_hash)
