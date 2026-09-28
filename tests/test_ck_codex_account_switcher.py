from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "ck-codex-account.py"


def run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CK_CODEX_ACCOUNTS_HOME"] = str(tmp_path / "accounts")
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_add_isolated_profile(tmp_path: Path) -> None:
    result = run(tmp_path, "add", "second-gmail")
    assert result.returncode == 0
    profile = tmp_path / "accounts" / "profiles" / "second-gmail"
    assert profile.is_dir()
    assert oct(profile.stat().st_mode & 0o777) == "0o700"

    metadata = json.loads((tmp_path / "accounts" / "accounts.json").read_text())
    assert metadata["accounts"]["second-gmail"]["created_at"]


def test_env_points_only_to_selected_profile(tmp_path: Path) -> None:
    assert run(tmp_path, "add", "one").returncode == 0
    result = run(tmp_path, "env", "one")
    assert result.returncode == 0
    assert "CODEX_HOME=" in result.stdout
    assert "profiles/one" in result.stdout


def test_remove_requires_confirmation(tmp_path: Path) -> None:
    assert run(tmp_path, "add", "one").returncode == 0
    refused = run(tmp_path, "remove", "one")
    assert refused.returncode != 0
    assert (tmp_path / "accounts" / "profiles" / "one").exists()

    removed = run(tmp_path, "remove", "one", "--confirm")
    assert removed.returncode == 0
    assert not (tmp_path / "accounts" / "profiles" / "one").exists()
