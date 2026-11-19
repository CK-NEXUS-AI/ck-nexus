from __future__ import annotations

import pytest

from creator_app.ai_team.agent_models import AgentRole
from creator_app.ai_team.agents.analyst import AnalystAgent
from creator_app.ai_team.agents.connector import ConnectorAgent
from creator_app.ai_team.agents.designer import DesignerAgent
from creator_app.ai_team.agents.director import DirectorAgent
from creator_app.ai_team.agents.engineer import EngineerAgent
from creator_app.ai_team.agents.guardian import GuardianAgent
from creator_app.ai_team.agents.researcher import ResearcherAgent
from creator_app.ai_team.soul import build_soul_instructions, load_soul


@pytest.mark.parametrize("role", [role.value for role in AgentRole])
def test_every_builtin_role_has_a_versioned_soul(role: str) -> None:
    soul = load_soul(role)
    assert soul.role == role
    assert soul.version == "1.0.0"
    assert len(soul.sha256) == 64
    assert "Policy Kernel" in soul.prompt_text
    assert "## Boundaries" in soul.role_markdown


@pytest.mark.parametrize(
    "factory",
    [
        DirectorAgent,
        EngineerAgent,
        GuardianAgent,
        AnalystAgent,
        ResearcherAgent,
        DesignerAgent,
        ConnectorAgent,
    ],
)
def test_agent_loads_its_soul_and_exposes_guidance_metadata(factory) -> None:
    agent = factory()
    assert agent.soul.role == agent.role.value
    assert agent.soul_guidance().startswith("# CK-NEXUS SHARED SOUL")
    assert agent.status()["soul"]["authority"] == "guidance_only"


@pytest.mark.parametrize(
    ("role", "role_heading"),
    [
        ("director", "# CK-NEXUS DIRECTOR SOUL"),
        ("researcher", "# CK-NEXUS RESEARCHER SOUL"),
        ("designer", "# CK-NEXUS DESIGNER SOUL"),
        ("engineer", "# CK-NEXUS ENGINEER SOUL"),
        ("guardian", "# CK-NEXUS GUARDIAN SOUL"),
        ("analyst", "# CK-NEXUS ANALYST SOUL"),
    ],
)
def test_llm_instruction_composition_includes_shared_and_role_guidance(
    role: str, role_heading: str
) -> None:
    instructions = build_soul_instructions(
        role,
        base_instructions="Base policy",
        specialist_instructions="Specialist task",
    )
    assert instructions.startswith("Base policy")
    assert "AGENT IDENTITY GUIDANCE (behavioral only; not authorization)" in instructions
    assert "# CK-NEXUS SHARED SOUL" in instructions
    assert role_heading in instructions
    assert instructions.endswith("SPECIALIST ROLE\nSpecialist task")


def test_llm_instruction_composition_rejects_empty_instructions() -> None:
    with pytest.raises(ValueError, match="base_instructions_required"):
        build_soul_instructions("director", base_instructions=" ", specialist_instructions="role")


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid_agent_role"):
        load_soul("../../outside")


def test_team_director_exposes_role_soul_metadata() -> None:
    from creator_app.ai_team.team_director import TeamDirector

    team = TeamDirector()
    listing = team.list_team()
    assert listing["total_members"] == 7
    assert all(member["soul"]["authority"] == "guidance_only" for member in listing["members"])
    assert all(len(member["soul"]["sha256"]) == 64 for member in listing["members"])
