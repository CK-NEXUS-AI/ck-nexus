from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class SandboxSessionState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass(slots=True)
class SandboxSession:
    session_id: str
    sandbox_kind: str
    policy_profile: str
    state: SandboxSessionState = SandboxSessionState.CREATED
    snapshots: list[str] = field(default_factory=list)

    def activate(self) -> None:
        if self.state not in {SandboxSessionState.CREATED, SandboxSessionState.PAUSED}:
            raise ValueError(f"cannot activate from {self.state}")
        self.state = SandboxSessionState.ACTIVE

    def pause(self) -> None:
        if self.state is not SandboxSessionState.ACTIVE:
            raise ValueError("only ACTIVE session can pause")
        self.state = SandboxSessionState.PAUSED

    def stop(self) -> None:
        if self.state is SandboxSessionState.STOPPED:
            return
        self.state = SandboxSessionState.STOPPED

    def snapshot(self, metadata: dict[str, Any]) -> str:
        if self.state not in {SandboxSessionState.ACTIVE, SandboxSessionState.PAUSED}:
            raise ValueError("snapshot requires ACTIVE or PAUSED session")
        canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(f"{self.session_id}:{canonical}".encode()).hexdigest()
        self.snapshots.append(digest)
        return digest
