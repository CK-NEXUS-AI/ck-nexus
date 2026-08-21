from __future__ import annotations

from pathlib import Path
from threading import Lock

from creator_app.agnes_ledger import AppendOnlyLedger


class DurableReplayLedger:
    """Append-only replay ledger for one-time approval nonces."""

    def __init__(self, path: Path) -> None:
        self.ledger = AppendOnlyLedger(path)
        self._lock = Lock()

    def is_redeemed(self, nonce: str) -> bool:
        if not nonce:
            return False
        return nonce in self._redeemed_nonces()

    def redeem_once(
        self,
        *,
        nonce: str,
        approval_id: str,
        actor_id: str,
        expires_at: float,
        subject_digest: str,
    ) -> None:
        if not all((nonce, approval_id, actor_id, subject_digest)):
            raise ValueError("replay ledger fields cannot be empty")
        with self._lock:
            redeemed = self._redeemed_nonces()
            if nonce in redeemed:
                raise PermissionError("approval token already redeemed")
            self.ledger.append(
                "approval_redeemed",
                {
                    "nonce": nonce,
                    "approval_id": approval_id,
                    "actor_id": actor_id,
                    "expires_at": expires_at,
                    "subject_digest": subject_digest,
                },
            )

    def verify(self) -> dict[str, object]:
        return self.ledger.verify().as_dict()

    def _redeemed_nonces(self) -> set[str]:
        state = self.ledger.verify()
        if not state.valid:
            raise RuntimeError(f"replay ledger integrity check failed: {state.error}")
        if not self.ledger.path.exists():
            return set()
        import json

        nonces: set[str] = set()
        with self.ledger.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("event_type") != "approval_redeemed":
                    continue
                payload = record.get("payload") or {}
                nonce = str(payload.get("nonce") or "")
                if nonce:
                    nonces.add(nonce)
        return nonces
