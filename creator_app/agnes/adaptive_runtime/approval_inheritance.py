from __future__ import annotations

from enum import IntEnum


class ApprovalMode(IntEnum):
    PLAN = 0
    DEFAULT = 1
    AUTO_EDIT = 2
    AUTONOMOUS = 3


def effective_child_mode(parent: ApprovalMode, child_requested: ApprovalMode) -> ApprovalMode:
    """A child may never be more permissive than its parent.

    CK-NEXUS intentionally chooses the stricter interpretation for delegated
    agents: delegation cannot be used as an authority-escalation path.
    """

    return min(parent, child_requested)
