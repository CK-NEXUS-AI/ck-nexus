"""Validate the repository's custom agent and skill metadata."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / ".github" / "agents"
SKILLS_DIR = ROOT / ".github" / "skills"
EXPECTED_AGENTS = {
    "cknexus-coordinator.agent.md",
    "cknexus-planner.agent.md",
    "cknexus-implementer.agent.md",
    "cknexus-security-reviewer.agent.md",
    "cknexus-test-verifier.agent.md",
    "cknexus-evidence-steward.agent.md",
    "cknexus-sre-recovery.agent.md",
}
ALLOWED_TOOLS = {"read", "search", "agent", "edit", "execute"}


def _frontmatter(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    _, frontmatter, _body = content.split("---\n", 2)
    name_match = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
    description_match = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
    tools_match = re.search(r"(?m)^tools:\s*\[(.*?)\]\s*$", frontmatter)
    assert name_match is not None
    assert description_match is not None
    assert description_match.group(1).strip().strip("\"'")
    if tools_match:
        tools = set(re.findall(r"[\w-]+", tools_match.group(1)))
        assert tools <= ALLOWED_TOOLS
    return name_match.group(1).strip().strip("\"'"), content


def test_expected_custom_agent_profiles_have_valid_metadata() -> None:
    paths = {path.name: path for path in AGENTS_DIR.glob("*.agent.md")}
    assert set(paths) >= EXPECTED_AGENTS
    for filename in EXPECTED_AGENTS:
        name, content = _frontmatter(paths[filename])
        assert name
        assert any(term in content.lower() for term in ("authority", "evidence", "owner"))
        assert "Q10" in content or "evidence" in content.lower()


def test_skills_have_matching_directory_names_and_descriptions() -> None:
    paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    assert len(paths) >= 5
    for path in paths:
        name, _content = _frontmatter(path)
        assert name == path.parent.name
