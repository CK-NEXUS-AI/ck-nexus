from __future__ import annotations

from pathlib import Path

import pytest

from scripts.dependency_preflight import load_requirements


def write_pyproject(path: Path) -> None:
    path.write_text(
        """
[project]
name = "sample"
version = "0.1.0"
dependencies = ["packaging>=20"]

[project.optional-dependencies]
dev = ["pytest>=8"]
billing = ["packaging>=20"]
""".strip(),
        encoding="utf-8",
    )


def test_load_requirements_deduplicates_distribution_names(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    write_pyproject(pyproject)
    requirements = load_requirements(pyproject, ("dev", "billing"))
    assert [item.name.lower() for item in requirements] == ["packaging", "pytest"]


def test_load_requirements_rejects_unknown_group(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    write_pyproject(pyproject)
    with pytest.raises(ValueError, match="unknown optional dependency group"):
        load_requirements(pyproject, ("missing",))
