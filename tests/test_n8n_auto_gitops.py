import json
import subprocess
from pathlib import Path

from creator_app.n8n_intelligence.auto_gitops import AutoGitOps


def _evidence(tmp_path: Path, **updates) -> tuple[Path, Path]:
    workspace = tmp_path / "worktrees" / "job1"
    workspace.mkdir(parents=True)
    (workspace / "creator_app").mkdir()
    (workspace / "creator_app" / "n8n_intelligence").mkdir(parents=True)
    (workspace / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
        "value = 2\n", encoding="utf-8"
    )
    data = {
        "job_id": "job-1",
        "state": "verified",
        "workspace": str(workspace),
        "branch": "cknexus/auto-dev/0123456789abcdef",
        "base_head": "base-sha",
        "tests_ok": True,
        "head_unchanged": True,
        "index_clean": True,
        "safe_paths": True,
        "changed_paths": ["creator_app/n8n_intelligence/analysis.py"],
    }
    data.update(updates)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    evidence_path = evidence_dir / "job-1.json"
    evidence_path.write_text(json.dumps(data), encoding="utf-8")
    return evidence_path, workspace


def test_unverified_evidence_never_stages_or_pushes(tmp_path: Path):
    evidence_path, _ = _evidence(tmp_path, state="verification_failed")
    gitops = AutoGitOps(
        tmp_path / "evidence", runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError())
    )
    result = gitops.run_once()
    assert result.state == "idle"
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["state"] == "verification_failed"


def test_forbidden_path_is_rejected_before_git_mutation(tmp_path: Path):
    evidence_path, _ = _evidence(tmp_path, changed_paths=[".env"])
    gitops = AutoGitOps(
        tmp_path / "evidence", runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError())
    )
    result = gitops.run_once()
    assert result.state == "blocked"
    assert result.reason == "path_not_allowlisted"
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["gitops_state"] == "blocked"


def test_verified_change_is_committed_and_pushed_to_its_branch(tmp_path: Path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "creator_app" / "n8n_intelligence").mkdir(parents=True)
    (repo / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
        "value = 1\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "creator_app/n8n_intelligence/analysis.py"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "push", "-u", "origin", "main"], check=True, capture_output=True
    )
    base_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    suffix = "0123456789abcdef"
    branch = f"cknexus/auto-dev/{suffix}"
    evidence_dir = tmp_path / "state" / "auto-dev"
    evidence_dir.mkdir(parents=True)
    workspace = evidence_dir.parent / "worktrees" / suffix
    workspace.parent.mkdir(parents=True)
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(workspace), "HEAD"],
        check=True,
        capture_output=True,
    )
    (workspace / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
        "value = 2\n", encoding="utf-8"
    )
    data = {
        "job_id": "job-push-test",
        "state": "verified",
        "workspace": str(workspace),
        "branch": branch,
        "base_head": base_head,
        "tests_ok": True,
        "head_unchanged": True,
        "index_clean": True,
        "safe_paths": True,
        "changed_paths": ["creator_app/n8n_intelligence/analysis.py"],
    }
    (evidence_dir / "job-push-test.json").write_text(json.dumps(data), encoding="utf-8")

    result = AutoGitOps(evidence_dir, repo_root=repo).run_once()

    assert result.state == "published"
    assert result.commit_sha
    remote_sha = subprocess.run(
        ["git", "--git-dir", str(remote), "rev-parse", f"refs/heads/{branch}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert remote_sha == result.commit_sha
    assert not workspace.exists()
    assert (repo / "creator_app" / "n8n_intelligence" / "analysis.py").read_text(
        encoding="utf-8"
    ) == "value = 1\n"


def test_protected_agent_and_policy_files_cannot_be_published(tmp_path: Path):
    evidence_path, _ = _evidence(
        tmp_path,
        branch="cknexus/auto-dev/0123456789abcdef",
        changed_paths=["creator_app/n8n_intelligence/auto_gitops.py"],
    )
    gitops = AutoGitOps(
        tmp_path / "evidence",
        runner=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("git must not run")),
    )
    result = gitops.run_once()
    assert result.state == "blocked"
    assert result.reason == "path_not_allowlisted"
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["gitops_state"] == "blocked"
