from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch


@dataclass(frozen=True, slots=True)
class SkillActivationPolicy:
    """Fail-closed skill activation without auto-granting tool authority.

    A skill may be visible/invocable while still requiring the existing
    CK-NEXUS Governor for any execution grant.
    """

    name: str
    path_patterns: tuple[str, ...] = field(default_factory=tuple)
    user_invocable: bool = True
    model_invocable: bool = True

    def is_active(
        self,
        *,
        touched_paths: tuple[str, ...] = (),
        explicit_user_invocation: bool = False,
    ) -> bool:
        if explicit_user_invocation:
            return self.user_invocable
        if not self.model_invocable:
            return False
        if not self.path_patterns:
            return True
        return any(
            fnmatch(path, pattern)
            for path in touched_paths
            for pattern in self.path_patterns
        )

    def grants_execution_authority(self) -> bool:
        """Skills never grant execution authority by themselves."""
        return False
