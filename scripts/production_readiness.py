from __future__ import annotations

"""Non-destructive CK-NEXUS production readiness aggregator.

This script never deploys, merges, pushes, rotates credentials, or changes infrastructure.
It combines local repository checks with explicit external-gate evidence. External gates
remain BLOCKED until their required evidence is supplied.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
        p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (p.stdout + p.stderr).strip().splitlines()
    return p.returncode == 0, (output[-1] if output else f"exit={p.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    compile_ok, compile_detail = command_ok(
        [sys.executable, "-m", "compileall", "-q", "creator_app", "main.py"]
    )

    gates = [
        Gate("LOCAL-FILES", "Canonical release files", "PASS" if not missing else "BLOCKED", 
             "all required files present" if not missing else "missing: " + ", ".join(missing)),
        Gate("LOCAL-COMPILE", "Python compile", "PASS" if compile_ok else "BLOCKED", compile_detail),
        Gate("Q10", "Repository-wide deep security scan", "BLOCKED",
             "Requires Codex Security Deep Security Scan evidence for the frozen runtime subject."),
        Gate("Q11", "Live provider smoke test", "BLOCKED",
             "Requires authorized staging OPENAI_API_KEY and successful verify/q11-final-subject."),
        Gate("Q12", "Delegated cgroup v2", "BLOCKED",
             "Requires non-root writable delegated cpu/memory/pids cgroup v2 on staging/self-hosted Linux."),
        Gate("Q13", "PostgreSQL disaster recovery", "PASS_CANDIDATE",
             "Existing release evidence; must be revalidated for the final subject."),
        Gate("Q14", "Observability/operator delivery", "PASS",
             "Existing release evidence; must be revalidated for the final subject."),
        Gate("Q15", "Clean-machine deployment", "PASS_CANDIDATE",
             "Existing release evidence; must be revalidated for the final subject."),
        Gate("Q16", "Production image/package", "PASS_CANDIDATE",
             "Existing release evidence; final package remains ineligible while Q10-Q12 are blocked."),
    ]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": "spinlnw10-art/ck-nexus",
        "mode": "non-destructive-readiness",
        "production_eligible": all(g.state == "PASS" for g in gates),
        "gates": [asdict(g) for g in gates],
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
