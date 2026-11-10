#!/usr/bin/env python3
"""Generate a read-only, evidence-derived Q10-Q16 status report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILES = {
    "Q10": ("evidence/Q10_DEPENDENCY_AUDIT.json",),
    "Q11": ("evidence/Q11_OPENAI_LIVE.json",),
    "Q12": ("evidence/Q12_CGROUP_V2.json",),
    "Q13": ("evidence/Q13_POSTGRES_DR.json",),
    "Q14": ("evidence/Q14_OBSERVABILITY_ALERT.json",),
    "Q15": ("evidence/Q15_CLEAN_MACHINE.json",),
    "Q16": (
        "evidence/Q16_PRODUCTION_IMAGE.json",
        "evidence/Q16_RUNTIME_LICENSE_SUMMARY.json",
    ),
}
RUNTIME_PATHS = (
    "app", "creator_app", "services", "gateway", "orchestration",
    "idea_engine", "migrations", "deploy", "observability", "Dockerfile",
    "docker-compose.prod.yml", "main.py", "pyproject.toml", "uv.lock",
)
STATUS_KEYS = ("gate_result", "result", "status", "component_result")
PASS_STATES = {"PASS", "VERIFIED"}
FAIL_STATES = {"FAIL", "FAILED", "ERROR"}
BLOCKED_STATES = {"BLOCKED", "NEED_MORE_EVIDENCE"}
NOT_VERIFIED_STATES = {"NOT_VERIFIED", "NOT_VERIFIED_YET"}
NOT_STARTED_STATES = {"NOT_STARTED", "MISSING", "NOT_RUN", "PENDING"}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "UNKNOWN"
    for key in STATUS_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper().replace(" ", "_")
    return "UNKNOWN"


def _evidence_status(payload: dict[str, Any] | None, root: Path) -> str:
    """Reject evidence whose source commit/tree no longer matches runtime files."""
    if not payload:
        return "UNKNOWN"
    source_sha = payload.get("source_sha")
    recorded_tree = payload.get("source_tree")
    if not isinstance(source_sha, str) or not source_sha.strip():
        return "UNKNOWN"
    commit = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{source_sha}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if commit.returncode:
        return "STALE"
    tree = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{source_sha}^{{tree}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if tree.returncode or not isinstance(recorded_tree, str):
        return "STALE"
    if tree.stdout.strip() != recorded_tree:
        return "STALE"
    changed = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", source_sha, "HEAD", "--", *RUNTIME_PATHS],
        capture_output=True,
        check=False,
    )
    if changed.returncode == 0:
        return _status(payload)
    return "STALE" if changed.returncode == 1 else "UNKNOWN"


def _combine_status(statuses: list[str]) -> str:
    if not statuses:
        return "UNKNOWN"
    if any(status == "STALE" for status in statuses):
        return "STALE"
    if any(status in FAIL_STATES for status in statuses):
        return "FAIL"
    if any(status in BLOCKED_STATES for status in statuses):
        return "BLOCKED"
    if any(status in NOT_VERIFIED_STATES for status in statuses):
        return "NOT_VERIFIED"
    if any(status in NOT_STARTED_STATES for status in statuses):
        return "NOT_STARTED"
    if any(status in {"PASS_CANDIDATE", "CANDIDATE"} for status in statuses):
        return "PASS_CANDIDATE"
    if all(status in PASS_STATES for status in statuses):
        return "PASS"
    return "UNKNOWN"


def gate_progress(status: str) -> int | None:
    """Return a percentage only for states with a defensible numeric index."""
    normalized = status.upper()
    if normalized in PASS_STATES:
        return 100
    if normalized in {"PASS_CANDIDATE", "CANDIDATE"}:
        return 75
    if normalized in NOT_STARTED_STATES:
        return 0
    return None


def aggregate_progress(values: list[int | None]) -> int | None:
    """Do not average blocked/failed/unknown states into a misleading percentage."""
    if not values or any(value is None for value in values):
        return None
    return int(sum(value for value in values if value is not None) / len(values) + 0.5)


def load_gate_states(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for gate, relative_paths in STATUS_FILES.items():
        statuses: list[str] = []
        sources: list[str] = []
        for relative_path in relative_paths:
            path = root / relative_path
            payload = _read_json(path)
            statuses.append(_evidence_status(payload, root))
            if payload is not None:
                sources.append(relative_path)
        status = _combine_status(statuses)
        result[gate] = {
            "status": status,
            "progress": gate_progress(status),
            "sources": sources,
        }
    return result


def group_states(gates: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    members = {
        "Security": ("Q10",),
        "Stability": ("Q11", "Q12"),
        "Release": ("Q13", "Q14"),
        "Delivery": ("Q15", "Q16"),
    }
    groups: dict[str, dict[str, Any]] = {}
    for name, gate_names in members.items():
        status = _combine_status([gates[gate]["status"] for gate in gate_names])
        progress = aggregate_progress([gates[gate]["progress"] for gate in gate_names])
        groups[name] = {"status": status, "progress": progress, "gates": list(gate_names)}
    return groups


def group_progress(gates: dict[str, dict[str, Any]]) -> dict[str, int | None]:
    return {name: item["progress"] for name, item in group_states(gates).items()}


def recent_commits(root: Path = ROOT, limit: int = 20) -> list[tuple[str, str, str]]:
    process = subprocess.run(
        [
            "git", "-C", str(root), "log", f"-{limit}",
            "--date=short", "--pretty=format:%h%x09%ad%x09%s",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        return []
    commits = []
    for line in process.stdout.splitlines():
        fields = line.split("\t", 2)
        if len(fields) == 3:
            commits.append(tuple(part.replace("|", "\\|") for part in fields))
    return commits


def render_report(root: Path = ROOT) -> str:
    gates = load_gate_states(root)
    groups = group_states(gates)
    tick = chr(96)
    lines = [
        "# CK-NEXUS Update Report",
        "",
        "> Generated from the current committed repository snapshot.",
        "> This report summarizes committed evidence; it is not "
        "production approval or certification.",
        "> Current release decision remains **NO-GO for Production**.",
        "",
        "## Q10–Q16 Gate Status",
        "",
        "| Gate | Evidence status | Status index | Evidence source |",
        "|---|---|---:|---|",
    ]
    for gate in ("Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q16"):
        item = gates[gate]
        progress = item["progress"]
        index = f"{progress}%" if progress is not None else item["status"].replace("_", " ")
        source = ", ".join(item["sources"]) or "missing"
        lines.append(f"| {gate} | **{item['status']}** | {index} | {source} |")

    lines.extend([
        "",
        "## Summary Badges",
        "",
        "| Security | Stability | Release | Delivery |",
        "|---|---|---|---|",
        "| "
        + " | ".join(
            f"**{name}: {item['status']}**"
            + (f" ({item['progress']}%)" if item["progress"] is not None else "")
            for name, item in groups.items()
        )
        + " |",
        "",
        "Status mapping: PASS = 100%; PASS_CANDIDATE = 75%; NOT_STARTED = 0%. "
        "FAIL, BLOCKED, NOT_VERIFIED, STALE, and UNKNOWN are shown as status "
        "labels, not percentages.",
        "Combined groups are numeric only when every member has a defensible numeric index.",
        "",
        "## Recent Commits",
        "",
        "| Commit | Date | Subject |",
        "|---|---|---|",
    ])
    commits = recent_commits(root)
    if commits:
        for sha, date, subject in commits:
            lines.append(f"| {tick}{sha}{tick} | {date} | {subject} |")
    else:
        lines.append("| — | — | Git history unavailable |")
    lines.extend([
        "",
        "## Authority Boundary",
        "",
        "These badges summarize the committed evidence files listed above. "
        "They do not change evidence, expected release subjects, gate decisions, "
        "Core Authority, or the NO-GO release decision.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    output = ROOT / "docs" / "UPDATE_REPORT.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(), encoding="utf-8")
    print(f"WROTE {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
