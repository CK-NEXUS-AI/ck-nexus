from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorktreeExecutionPolicy:
    """Select safe execution mode for delegated coding work.

    Background execution is allowed only for CK-managed isolated worktrees.
    Caller-owned worktrees remain foreground to preserve ownership and avoid
    hidden concurrent mutation.
    """

    ck_managed_isolation: bool
    caller_owned_worktree: bool
    requested_background: bool

    def execution_mode(self) -> str:
        if self.caller_owned_worktree:
            return "FOREGROUND"
        if self.requested_background and self.ck_managed_isolation:
            return "BACKGROUND_GOVERNED"
        return "FOREGROUND"

    def can_fork_context(self) -> bool:
        return self.ck_managed_isolation and not self.caller_owned_worktree
