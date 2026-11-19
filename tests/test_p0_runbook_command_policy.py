import sys

import pytest

from runbooks import p0_runbook_v3 as runbook


def test_runbook_rejects_unapproved_executable():
    with pytest.raises(ValueError, match="executable"):
        runbook._validate_runbook_command(["python", "-c", "print(1)"])


def test_runbook_rejects_shell_inline_commands():
    with pytest.raises(ValueError, match="shell script"):
        runbook._validate_runbook_command(["bash", "-c", "echo unsafe"])


def test_runbook_accepts_repository_python_script():
    runbook._validate_runbook_command(
        [sys.executable, str(runbook.ROOT / "scripts/gate_email_routing.py")]
    )


def test_runbook_rejects_script_outside_repository():
    with pytest.raises(ValueError, match="inside the repository"):
        runbook._validate_runbook_command([sys.executable, "/tmp/attacker.py"])
