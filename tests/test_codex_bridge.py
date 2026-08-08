from __future__ import annotations

import stat
from pathlib import Path

import pytest

from creator_app.codex_bridge import CodexBridge, CodexBridgeUnavailableError
from creator_app.config import Settings


def _fake_codex(tmp_path: Path) -> Path:
    executable = tmp_path / "codex"
    executable.write_text(
        """#!/usr/bin/env python3
import pathlib
import sys

output_path = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])
prompt = sys.stdin.read()
output_path.write_text('completed: ' + prompt.split('USER TASK', 1)[-1].strip())
""",
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


@pytest.mark.asyncio
async def test_codex_bridge_runs_without_a_shell(tmp_path: Path):
    executable = _fake_codex(tmp_path)
    settings = Settings(
        database_path=tmp_path / "test.db",
        codex_enabled=True,
        codex_bin=str(executable),
        codex_workspace=tmp_path,
    )
    result = await CodexBridge(settings).run("Inspect the project")
    assert result.output == "completed: Inspect the project"
    assert result.duration_ms >= 1


@pytest.mark.asyncio
async def test_codex_bridge_is_disabled_by_default(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "test.db", codex_workspace=tmp_path)
    with pytest.raises(CodexBridgeUnavailableError, match="disabled"):
        await CodexBridge(settings).run("Inspect the project")
