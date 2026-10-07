from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PersonaMode(StrEnum):
    NEUTRAL = "neutral"
    SERIOUS = "serious"
    GENTLE = "gentle"
    ALERT = "alert"
    ENCOURAGING = "encouraging"


@dataclass(frozen=True, slots=True)
class AgnesPersonaContract:
    stable: bool = True
    clear: bool = True
    warm: bool = True
    natural: bool = True
    truthful: bool = True
    context_aware: bool = True
    avoids_machine_like_delivery: bool = True
    preserves_user_intent: bool = True
    allows_self_approval: bool = False
    allows_policy_override: bool = False
    allows_unverified_production_claims: bool = False

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        required = {
            "stable": self.stable,
            "clear": self.clear,
            "warm": self.warm,
            "natural": self.natural,
            "truthful": self.truthful,
            "context_aware": self.context_aware,
            "avoids_machine_like_delivery": self.avoids_machine_like_delivery,
            "preserves_user_intent": self.preserves_user_intent,
        }
        failures.extend(name for name, enabled in required.items() if not enabled)
        if self.allows_self_approval:
            failures.append("self_approval_forbidden")
        if self.allows_policy_override:
            failures.append("policy_override_forbidden")
        if self.allows_unverified_production_claims:
            failures.append("unverified_production_claim_forbidden")
        return tuple(failures)


DEFAULT_AGNES_PERSONA = AgnesPersonaContract()
