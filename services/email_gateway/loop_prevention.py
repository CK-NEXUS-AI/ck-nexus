from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class LoopDecision:
    allow_automatic_reply: bool
    reason: str


def evaluate_loop_headers(headers: Mapping[str, str], *, system_addresses: set[str] | None = None) -> LoopDecision:
    normalized = {key.casefold(): value.strip() for key, value in headers.items()}
    auto_submitted = normalized.get("auto-submitted", "no").casefold()
    precedence = normalized.get("precedence", "").casefold()
    from_address = normalized.get("from", "").casefold()

    if normalized.get("x-ck-nexus-loop") or normalized.get("x-ck-nexus-automation"):
        return LoopDecision(False, "ck_nexus_automation_header")
    if auto_submitted not in {"", "no"}:
        return LoopDecision(False, "auto_submitted_message")
    if precedence in {"bulk", "list", "junk"}:
        return LoopDecision(False, f"precedence_{precedence}")
    if system_addresses and any(address.casefold() in from_address for address in system_addresses):
        return LoopDecision(False, "system_sender")
    if "mailer-daemon" in from_address or "postmaster" in from_address:
        return LoopDecision(False, "delivery_status_sender")
    return LoopDecision(True, "reply_allowed")


def outbound_loop_headers(event_id: str, workflow: str) -> dict[str, str]:
    return {
        "Auto-Submitted": "auto-replied",
        "X-CK-NEXUS-Automation": "true",
        "X-CK-NEXUS-Loop": event_id,
        "X-CK-NEXUS-Workflow": workflow,
        "X-CK-NEXUS-Event-ID": event_id,
    }
