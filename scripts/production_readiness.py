"""Non-destructive CK-NEXUS production readiness aggregator.

This script never deploys, merges, pushes, rotates credentials, or changes infrastructure.
It combines local repository checks with explicit external-gate evidence. External gates
remain BLOCKED until their required evidence is supplied.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "scripts/release_check.py",
    "docs/RELEASE_CHECKLIST.md",
    "RELEASE_STATUS.md",
)


@dataclass(frozen=True)
class Gate:
    id: str
    name: str
    state: str
    evidence: str


def command_ok(command: list[str]) -> tuple[bool, str]:
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (process.stdout + process.stderr).strip().splitlines()
    return process.returncode == 0, (output[-1] if output else f"exit={process.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    compile_ok, compile_detail = command_ok(
        [sys.executable, "-m", "compileall", "-q", "creator_app", "main.py"]
    )

    gates = [
        Gate(
            "LOCAL-FILES",
            "Canonical release files",
            "PASS" if not missing else "BLOCKED",
            "all required files present" if not missing else "missing: " + ", ".join(missing),
        ),
        Gate(
            "LOCAL-COMPILE",
            "Python compile",
            "PASS" if compile_ok else "BLOCKED",
            compile_detail,
        ),
        Gate(
            "Q10",
            "Open-source layered security scan",
            "BLOCKED",
            "Requires open-source layered security evidence bound to the frozen runtime subject "
            "(Bandit, secret scan, pip-audit, and attack regression).",
        ),
        Gate(
            "Q11",
            "Live provider smoke test",
            "BLOCKED",
            "Requires authorized staging OPENAI_API_KEY and successful verify/q11-final-subject.",
        ),
        Gate(
            "Q12",
            "Delegated cgroup v2",
            "BLOCKED",
            "Requires non-root writable delegated cpu/memory/pids cgroup v2 on "
            "staging/self-hosted Linux.",
        ),
        Gate(
            "Q13",
            "PostgreSQL disaster recovery",
            "PASS_CANDIDATE",
            "Existing release evidence; must be revalidated for the final subject.",
        ),
        Gate(
            "Q14",
            "Observability/operator delivery",
            "PASS",
            "Existing release evidence; must be revalidated for the final subject.",
        ),
        Gate(
            "Q15",
            "Clean-machine deployment",
            "PASS_CANDIDATE",
            "Existing release evidence; must be revalidated for the final subject.",
        ),
        Gate(
            "Q16",
            "Production image/package",
            "PASS_CANDIDATE",
            "Existing release evidence; final package remains ineligible while "
            "Q10-Q12 are blocked.",
        ),
    ]

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": "spinlnw10-art/ck-nexus",
        "mode": "non-destructive-readiness",
        "production_eligible": all(gate.state == "PASS" for gate in gates),
        "gates": [asdict(gate) for gate in gates],
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("CK-NEXUS PRODUCTION READINESS")
    print("=" * 32)
    for gate in gates:
        print(f"[{gate.state:14}] {gate.id:12} {gate.name} — {gate.evidence}")
    print()
    print("PRODUCTION_ELIGIBLE=", result["production_eligible"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
