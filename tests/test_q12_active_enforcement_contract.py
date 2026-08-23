import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts/q12/active_cgroup_enforcement_probe.py"
WORKFLOW = ROOT / ".github/workflows/verify-q12-final-subject.yml"


def test_q12_active_probe_refuses_non_staging(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["CKNEXUS_ENVIRONMENT"] = "production"
    result = subprocess.run(
        [sys.executable, str(PROBE), "--root", str(tmp_path)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "BLOCKED"


def test_q12_active_probe_refuses_root_cgroup_mount() -> None:
    env = dict(os.environ)
    env["CKNEXUS_ENVIRONMENT"] = "staging"
    result = subprocess.run(
        [sys.executable, str(PROBE), "--root", "/sys/fs/cgroup"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "BLOCKED",
        "reason": "dedicated_delegated_root_required",
    }


def test_q12_authoritative_workflow_is_manual_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "\n  push:" not in text
    assert "runs-on: [self-hosted, linux, cknexus-q12]" in text


def test_q12_requires_active_kernel_evidence_before_pass() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "configured_limits_verified" in text
    assert "active_kernel_enforcement" in text
    assert "actual_kernel_enforcement" in text
    assert "assert x['configured_limits_verified'] is True" in text
    assert "assert x['active_kernel_enforcement'] is True" in text
    assert "q12-verifier-sha.txt" in text
    assert "q12-verifier-tree.txt" in text
