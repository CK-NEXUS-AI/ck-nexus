from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = "CK-NEXUS-AI/ck-nexus"
BRANCH = "release/q10-q16-closure-20261105"
GATES = {
    "Q10": (
        "q10-open-source-security-",
        "Q10_DEPENDENCY_AUDIT.json",
        ".github/workflows/q10-evidence-gate.yml",
    ),
    "Q11": ("q11-final-", "Q11_OPENAI_LIVE.json", ".github/workflows/verify-q11-final-subject.yml"),
    "Q12": ("q12-final-", "Q12_CGROUP_V2.json", ".github/workflows/verify-q12-final-subject.yml"),
    "Q13": (
        "q13-postgres-dr-",
        "Q13_POSTGRES_DR.json",
        ".github/workflows/candidate-automated-gates.yml",
    ),
    "Q14": (
        "q14-final-",
        "Q14_OBSERVABILITY_ALERT.json",
        ".github/workflows/verify-q14-final-subject.yml",
    ),
    "Q15": (
        "q15-clean-machine-",
        "Q15_CLEAN_MACHINE.json",
        ".github/workflows/candidate-automated-gates.yml",
    ),
    "Q16_PRODUCTION_IMAGE": (
        "q16-production-image-",
        "Q16_PRODUCTION_IMAGE.json",
        ".github/workflows/candidate-production-image.yml",
    ),
    "Q16_RUNTIME_LICENSES": (
        "q16-runtime-licenses-",
        "Q16_RUNTIME_LICENSE_SUMMARY.json",
        ".github/workflows/candidate-runtime-licenses.yml",
    ),
}


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}: {result.stderr[-500:]}"
        )
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise TypeError("expected JSON object from GitHub CLI")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect exact-subject CK-NEXUS Q10-Q16 workflow evidence."
    )
    parser.add_argument("--q10", type=int, required=True)
    parser.add_argument("--q11", type=int, required=True)
    parser.add_argument("--q12", type=int, required=True)
    parser.add_argument("--q13", type=int, required=True)
    parser.add_argument("--q14", type=int, required=True)
    parser.add_argument("--q15", type=int, required=True)
    parser.add_argument("--q16-image", type=int, required=True)
    parser.add_argument("--q16-licenses", type=int, required=True)
    parser.add_argument("--repo", default=REPOSITORY)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evidence"))
    args = parser.parse_args()

    evidence_dir = args.evidence_dir
    release = json.loads((evidence_dir / "RELEASE_SUBJECT.json").read_text(encoding="utf-8"))
    expected_subject = release["runtime_subject_manifest_sha256"]
    if release.get("candidate_branch") != BRANCH:
        raise SystemExit("RELEASE_SUBJECT.json candidate branch mismatch")
    run_ids = {
        "Q10": args.q10,
        "Q11": args.q11,
        "Q12": args.q12,
        "Q13": args.q13,
        "Q14": args.q14,
        "Q15": args.q15,
        "Q16_PRODUCTION_IMAGE": args.q16_image,
        "Q16_RUNTIME_LICENSES": args.q16_licenses,
    }
    collected: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="cknexus-release-evidence-") as temporary:
        temp_root = Path(temporary)
        for gate, (prefix, evidence_name, workflow_path) in GATES.items():
            run_id = run_ids[gate]
            run = run_json(["gh", "api", f"repos/{args.repo}/actions/runs/{run_id}"])
            if (
                run.get("head_branch") != BRANCH
                or run.get("conclusion") != "success"
                or run.get("status") != "completed"
                or run.get("event") != "workflow_dispatch"
                or run.get("path") != workflow_path
            ):
                raise SystemExit(
                    f"{gate}: workflow run path/event/status/branch/conclusion mismatch"
                )
            artifacts_response = run_json(
                ["gh", "api", f"repos/{args.repo}/actions/runs/{run_id}/artifacts?per_page=100"]
            )
            artifacts = artifacts_response.get("artifacts", [])
            artifact_name = f"{prefix}{run.get('head_sha')}"
            matches = [item for item in artifacts if item.get("name") == artifact_name]
            if len(matches) != 1:
                raise SystemExit(f"{gate}: expected exactly one artifact named {artifact_name}")
            artifact = matches[0]
            workflow_run = artifact.get("workflow_run") or {}
            if (
                workflow_run.get("id") != run_id
                or workflow_run.get("head_sha") != run.get("head_sha")
                or workflow_run.get("head_branch") != BRANCH
            ):
                raise SystemExit(f"{gate}: artifact workflow-run binding mismatch")
            if artifact.get("expired") is not False:
                raise SystemExit(f"{gate}: artifact expired or expiry state unknown")
            digest = artifact.get("digest")
            if not isinstance(digest, str) or not digest.startswith("sha256:"):
                raise SystemExit(f"{gate}: GitHub artifact digest missing")
            download_dir = temp_root / gate.lower()
            download_dir.mkdir(parents=True)
            subprocess.run(
                [
                    "gh",
                    "run",
                    "download",
                    str(run_id),
                    "--repo",
                    args.repo,
                    "--name",
                    artifact_name,
                    "--dir",
                    str(download_dir),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            downloaded = download_dir / evidence_name
            if not downloaded.is_file():
                raise SystemExit(f"{gate}: artifact missing {evidence_name}")
            evidence = json.loads(downloaded.read_text(encoding="utf-8"))
            if evidence.get("source_sha") != run.get("head_sha"):
                raise SystemExit(
                    f"{gate}: evidence source SHA does not match workflow run head SHA"
                )
            if evidence.get("release_subject_manifest_sha256") != expected_subject:
                raise SystemExit(f"{gate}: evidence runtime subject mismatch")
            if evidence.get("github_run_id") != run_id:
                raise SystemExit(f"{gate}: evidence run ID mismatch")
            evidence.update(
                {
                    "artifact_id": int(artifact["id"]),
                    "artifact_digest": digest,
                    "artifact_name": artifact_name,
                    "artifact_created_at": artifact.get("created_at"),
                    "artifact_expires_at": artifact.get("expires_at"),
                    "github_run_head_sha": run.get("head_sha"),
                    "github_run_head_branch": run.get("head_branch"),
                    "github_run_conclusion": run.get("conclusion"),
                    "github_run_event": run.get("event"),
                    "workflow_path": run.get("path"),
                    "workflow_name": run.get("name"),
                    "workflow_url": run.get("html_url"),
                }
            )
            target = evidence_dir / evidence_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            collected[gate] = {
                "run_id": run_id,
                "head_sha": run.get("head_sha"),
                "artifact_id": artifact["id"],
                "artifact_name": artifact_name,
                "artifact_digest": digest,
                "artifact_expires_at": artifact.get("expires_at"),
                "evidence_file": evidence_name,
            }

    candidate = json.loads((evidence_dir / "Q10_DEPENDENCY_AUDIT.json").read_text(encoding="utf-8"))
    candidate_sha = candidate.get("source_sha")
    candidate_tree = candidate.get("source_tree")
    if not candidate_sha or not candidate_tree:
        raise SystemExit("Q10 evidence does not provide candidate source SHA/tree")
    for gate, item in collected.items():
        evidence = json.loads((evidence_dir / item["evidence_file"]).read_text(encoding="utf-8"))
        if (
            evidence.get("source_sha") != candidate_sha
            or evidence.get("source_tree") != candidate_tree
        ):
            raise SystemExit(f"{gate}: source SHA/tree differs from Q10 candidate")

    manifest = {
        "schema_version": 1,
        "repository": args.repo,
        "candidate_branch": BRANCH,
        "candidate_source_sha": candidate_sha,
        "candidate_source_tree": candidate_tree,
        "runtime_subject_manifest_sha256": expected_subject,
        "collected_at": datetime.now(UTC).isoformat(),
        "artifacts": collected,
    }
    (evidence_dir / "ARTIFACT_PROVENANCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
