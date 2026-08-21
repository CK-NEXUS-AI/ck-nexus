from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    ARCHITECT = "architect"
    BUILDER = "builder"
    UPDATER = "updater"
    VERIFIER = "verifier"
    RED_TEAM = "red_team"
    GOVERNOR = "governor"
    RESEARCHER = "researcher"
    SCOUT = "scout"
    PROTOTYPE_BUILDER = "prototype_builder"
    EVALUATOR = "evaluator"
    CHALLENGER = "challenger"


TRACK_A_ROLES = {
    AgentRole.ARCHITECT,
    AgentRole.BUILDER,
    AgentRole.UPDATER,
    AgentRole.VERIFIER,
    AgentRole.RED_TEAM,
    AgentRole.GOVERNOR,
}

TRACK_B_ROLES = {
    AgentRole.RESEARCHER,
    AgentRole.SCOUT,
    AgentRole.PROTOTYPE_BUILDER,
    AgentRole.EVALUATOR,
    AgentRole.CHALLENGER,
}
