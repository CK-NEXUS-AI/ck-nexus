from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "ck-codex-account.py"


def run(tmp_path: Path, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CK_CODEX_ACCOUNTS_HOME"] = str(tmp_path / "accounts")
    if extra_env:
        env.update(extra_env)
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


def test_run_uses_selected_profile_and_strips_api_keys(tmp_path: Path) -> None:
    assert run(tmp_path, "add", "one").returncode == 0
    output = tmp_path / "child-env.json"
    code = (
        "import json, os, sys; "
        "json.dump({'home': os.environ.get('CODEX_HOME'), "
        "'openai': os.environ.get('OPENAI_API_KEY'), "
        "'codex': os.environ.get('CODEX_API_KEY')}, open(sys.argv[1], 'w'))"
    )
    result = run(
        tmp_path,
        "run",
        "one",
        "--",
        sys.executable,
        "-c",
        code,
        str(output),
        extra_env={"OPENAI_API_KEY": "redacted-test-key", "CODEX_API_KEY": "redacted-test-key-2"},
    )
    assert result.returncode == 0
    child = json.loads(output.read_text())
    assert child["home"] == str(tmp_path / "accounts" / "profiles" / "one")
    assert child["openai"] is None
    assert child["codex"] is None


def test_login_delegates_device_auth_and_marks_active(tmp_path: Path) -> None:
    log = tmp_path / "cli-args.txt"
    fake = tmp_path / "fake-codex"
    fake.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > {log}\n"
        "exit 0\n"
    )
    fake.chmod(0o700)

    result = run(
        tmp_path,
        "login",
        "second-gmail",
        extra_env={"CKNEXUS_CODEX_BIN": str(fake)},
    )
    assert result.returncode == 0
    assert log.read_text().splitlines() == ["login", "--device-auth"]
    metadata = json.loads((tmp_path / "accounts" / "accounts.json").read_text())
    assert metadata["active"] == "second-gmail"
