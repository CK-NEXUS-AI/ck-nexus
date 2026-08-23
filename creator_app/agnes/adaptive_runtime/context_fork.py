from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextForkPlan:
    """Describe a bounded child-context fork.

    The plan carries no authority and never includes raw credentials.
    It is metadata for the parent runtime to decide what context window may be
    copied to a child agent while preserving cache-friendly shared prefixes.
    """

    recent_user_turns: int | None = None
    inherit_system_context: bool = True
    share_prompt_cache_prefix: bool = True
    include_tool_outputs: bool = False

    def validate(self) -> None:
        if self.recent_user_turns is not None and self.recent_user_turns <= 0:
            raise ValueError("recent_user_turns must be positive or None")

    def mode(self) -> str:
        self.validate()
        if self.recent_user_turns is None:
            return "FULL_PARENT_CONTEXT"
        return f"LAST_{self.recent_user_turns}_USER_TURNS"
