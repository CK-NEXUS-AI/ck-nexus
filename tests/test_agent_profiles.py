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
ROLE_SIGNALS = {
    "cknexus-coordinator.agent.md": ("advisory coordinator", "delegate planning"),
    "cknexus-planner.agent.md": ("planning specialist", "rollback"),
    "cknexus-implementer.agent.md": ("implementation specialist", "regression tests"),
    "cknexus-security-reviewer.agent.md": ("security reviewer", "adversarial"),
    "cknexus-test-verifier.agent.md": ("test and verification specialist", "reproduce the failure"),
    "cknexus-evidence-steward.agent.md": ("evidence integrity specialist", "subject commit/tree"),
    "cknexus-sre-recovery.agent.md": ("sre and recovery specialist", "reconnection"),
}


def _frontmatter(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    _, frontmatter, _body = content.split("---\n", 2)
    name_match = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
    description_match = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
    assert name_match is not None
    assert description_match is not None
    assert description_match.group(1).strip().strip("\"'")

    lines = frontmatter.splitlines()
    tool_index = next(
        (index for index, line in enumerate(lines) if re.match(r"^tools\s*:", line)),
        None,
    )
    if tool_index is not None:
        value = lines[tool_index].split(":", 1)[1].strip()
        if value.startswith("[") and value.endswith("]"):
            tools = re.findall(r"[\w-]+", value[1:-1])
        elif value:
            tools = [value.strip("\"'")]
        else:
            tools = []
            for line in lines[tool_index + 1 :]:
                if line.strip() and not line.startswith((" ", "\t", "-")):
                    break
                if line.lstrip().startswith("-"):
                    item = line.lstrip()[1:].strip().strip("\"'")
                    assert item, "tools list contains an empty item"
                    tools.append(item)
        assert tools, "tools key is present but its value could not be parsed"
        assert set(tools) <= ALLOWED_TOOLS

    return name_match.group(1).strip().strip("\"'"), content


def test_expected_custom_agent_profiles_have_valid_metadata() -> None:
    paths = {path.name: path for path in AGENTS_DIR.glob("*.agent.md")}
    assert set(paths) >= EXPECTED_AGENTS
    for filename in EXPECTED_AGENTS:
        name, content = _frontmatter(paths[filename])
        assert name
        lowered = content.lower()
        assert all(signal in lowered for signal in ROLE_SIGNALS[filename])
        assert "Q10" in content or "evidence" in lowered


def test_skills_have_matching_directory_names_and_descriptions() -> None:
    paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    assert len(paths) >= 5
    for path in paths:
        name, _content = _frontmatter(path)
        assert name == path.parent.name


def test_frontmatter_validates_multiline_tool_allowlist(tmp_path):
    valid = tmp_path / "valid.agent.md"
    valid.write_text(
        "---\nname: valid\ndescription: valid profile\ntools:\n  - read\n  - search\n---\nbody\n",
        encoding="utf-8",
    )
    assert _frontmatter(valid)[0] == "valid"

    invalid = tmp_path / "invalid.agent.md"
    invalid.write_text(
        (
            "---\nname: invalid\ndescription: invalid profile\n"
            "tools:\n  - read\n  - shell\n---\nbody\n"
        ),
        encoding="utf-8",
    )
    try:
        _frontmatter(invalid)
    except AssertionError:
        pass
    else:
        raise AssertionError("unsupported multiline tool was accepted")
