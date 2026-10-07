from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
ALLOWED_JOB_WRITES = {
    (".github/workflows/trusted-verifier-image-ci.yml", "packages"),
}

errors: list[str] = []

for path in sorted(list(WORKFLOW_DIR.glob("*.yml")) + list(WORKFLOW_DIR.glob("*.yaml"))):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if re.search(r"(?m)^permissions:\s*write-all\s*$", text):
        errors.append(f"{path}: workflow-level write-all is forbidden")
        continue

    top = None
    for idx, line in enumerate(lines):
        if line == "permissions:":
            top = idx
            break
    if top is None:
        errors.append(f"{path}: missing top-level permissions block")
        continue

    block: list[str] = []
    for line in lines[top + 1 :]:
        if line and not line.startswith(" "):
            break
        block.append(line)

    if not any(re.match(r"^  contents:\s*read\s*$", line) for line in block):
        errors.append(f"{path}: top-level permissions must include contents: read")

    for line in block:
        m = re.match(r"^  ([a-z-]+):\s*write\s*$", line)
        if m:
            errors.append(f"{path}: top-level {m.group(1)}: write is forbidden; scope it to a job")

    current_job = None
    in_jobs = False
    for line in lines:
        if line == "jobs:":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        m_job = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if m_job:
            current_job = m_job.group(1)
            continue
        m_write = re.match(r"^      ([a-z-]+):\s*write\s*$", line)
        if m_write:
            perm = m_write.group(1)
            if (str(path), perm) not in ALLOWED_JOB_WRITES:
                errors.append(f"{path}:{current_job}: unexpected job-level {perm}: write")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("workflow permissions policy: PASS")
