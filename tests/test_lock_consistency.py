from __future__ import annotations

from pathlib import Path

from scripts.gate_lock_consistency import evaluate


def test_detects_missing_direct_dependency(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    pyproject.write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["fastapi>=0.1", "asyncpg>=0.30"]
[project.optional-dependencies]
dev = ["ruff>=0.1"]
""".strip(),
        encoding="utf-8",
    )
    lock.write_text(
        """
version = 1
[[package]]
name = "fastapi"
version = "1.0.0"
[[package]]
name = "ruff"
version = "0.12.0"
""".strip(),
        encoding="utf-8",
    )

    required, missing = evaluate(pyproject, lock, ("dev",))
    assert required == {"fastapi", "asyncpg", "ruff"}
    assert missing == {"asyncpg"}


def test_accepts_complete_lock(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    pyproject.write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["fastapi>=0.1"]
[project.optional-dependencies]
dev = ["ruff>=0.1"]
""".strip(),
        encoding="utf-8",
    )
    lock.write_text(
        """
version = 1
[[package]]
name = "fastapi"
version = "1.0.0"
[[package]]
name = "ruff"
version = "0.12.0"
""".strip(),
        encoding="utf-8",
    )

    _, missing = evaluate(pyproject, lock, ("dev",))
    assert not missing
