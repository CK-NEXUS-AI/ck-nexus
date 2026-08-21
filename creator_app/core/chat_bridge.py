from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class BridgeMode(StrEnum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"


class BridgeCommand(BaseModel):
    command: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)


class BridgeResponse(BaseModel):
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    live_executed: bool = False


class ChatBridgePolicy(BaseModel):
    mode: BridgeMode = BridgeMode.DISABLED
    allowed_commands: set[str] = Field(
        default_factory=lambda: {
            "status",
            "memory.status",
            "swarm.status",
            "inspect",
            "verify",
            "explain",
        }
    )
    production_mutation_allowed: bool = False
    external_write_allowed: bool = False
    require_governor_for_enable: bool = True


class CKNexusChatBridge:
    """Provider-neutral read-only chat bridge contract.

    This component does not perform network calls or production mutations.
    Runtime adapters may supply read handlers after explicit enablement.
    """

    def __init__(self, policy: ChatBridgePolicy | None = None) -> None:
        self.policy = policy or ChatBridgePolicy()
        self._handlers: dict[str, Any] = {}

    def register_read_handler(self, command: str, handler: Any) -> None:
        if command not in self.policy.allowed_commands:
            raise ValueError("command is not allowed by bridge policy")
        self._handlers[command] = handler

    def enable_read_only(self, *, governor_approved: bool) -> None:
        if self.policy.require_governor_for_enable and not governor_approved:
            raise PermissionError("CK Governor approval is required")
        self.policy.mode = BridgeMode.READ_ONLY

    def disable(self) -> None:
        self.policy.mode = BridgeMode.DISABLED

    def execute(self, request: BridgeCommand) -> BridgeResponse:
        if self.policy.mode != BridgeMode.READ_ONLY:
            raise PermissionError("chat bridge is disabled")
        if request.command not in self.policy.allowed_commands:
            raise PermissionError("command is blocked by bridge policy")
        if self.policy.production_mutation_allowed or self.policy.external_write_allowed:
            raise RuntimeError("read-only bridge policy was weakened")

        handler = self._handlers.get(request.command)
        if handler is None:
            return BridgeResponse(
                status="NOT_CONNECTED",
                data={"command": request.command},
                live_executed=False,
            )

        result = handler(request.args)
        if not isinstance(result, dict):
            raise TypeError("read handler must return a dict")
        return BridgeResponse(
            status="OK",
            data=result,
            live_executed=True,
        )
