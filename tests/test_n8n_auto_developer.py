import json
import shutil
import subprocess
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence import auto_developer as auto_developer_module
from creator_app.n8n_intelligence.auto_developer import AutoDeveloper


def _queue(tmp_path: Path, payload: dict) -> TaskStore:
    store = TaskStore(tmp_path / "tasks.db")
    store.enqueue("n8n-job-1", payload)
    return store


def _safe_payload() -> dict:
    return {
        "handler": "n8n_development_signal",
        "task": "Fix the failing workflow adapter",
        "description": "Fix the failing workflow adapter",
        "production_status": "NO-GO",
        "external_mutation_authorized": False,
    }


def test_ineligible_task_is_not_claimed(tmp_path: Path):
    payload = _safe_payload()
    payload["handler"] = "unapproved_handler"
    store = _queue(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()

    def runner(*args, **kwargs):
        raise AssertionError("ineligible tasks must not invoke tools")

    result = AutoDeveloper(
        store, repo=repo, evidence_dir=tmp_path / "evidence", runner=runner
    ).run_once()
    assert result.state == "blocked"
    assert result.reason == "handler_not_allowed"
    assert store.peek_next()["state"] == "queued"


def test_command_like_task_is_data_not_command(tmp_path: Path):
    payload = _safe_payload()
    payload["description"] = "rm -rf /; git push --force"
    store = _queue(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()

    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, "", "")

    result = AutoDeveloper(
        store, repo=repo, evidence_dir=tmp_path / "evidence", runner=runner
    ).run_once()
    assert result.state == "blocked"
    assert result.reason == "command_like_input"


def test_successful_run_requires_tests_and_keeps_head_unchanged(tmp_path: Path, monkeypatch):
    store = _queue(tmp_path, _safe_payload())
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(auto_developer_module, "DEFAULT_WORKSPACE_ROOT", tmp_path / "worktrees")
    state = {"head": "abc", "status": ""}
    opencode_commands = []

    def runner(args, **kwargs):
        if args[:3] == ["git", "show-ref", "--verify"]:
            return subprocess.CompletedProcess(args, 1, "", "")
        if args[:3] == ["git", "worktree", "add"]:
            Path(args[-2]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "status", "--porcelain=v1"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, state["head"] + "\n", "")
        if args[:3] == ["git", "diff", "--check"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0].endswith("pytest") and args[1:] == ["-q"]:
            return subprocess.CompletedProcess(args, 0, "1 passed\n", "")
        if args[:2] == ["opencode", "run"]:
            opencode_commands.append(args)
            return subprocess.CompletedProcess(args, 0, "implemented\n", "")
        raise AssertionError(args)

    result = AutoDeveloper(
        store, repo=repo, evidence_dir=tmp_path / "evidence", runner=runner
    ).run_once()
    assert result.state == "verified", result
    assert result.tests_ok is True
    assert opencode_commands and "--dir" in opencode_commands[0]
    assert "--auto" not in opencode_commands[0]
    assert store.get("n8n-job-1")["state"] == "completed"
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert evidence["head_unchanged"] is True
    assert evidence["index_clean"] is True


def test_dirty_primary_repo_uses_isolated_git_worktree(tmp_path: Path, monkeypatch):

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "creator_app" / "n8n_intelligence").mkdir(parents=True)
    (repo / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
        "baseline = True\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "creator_app/n8n_intelligence/analysis.py"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
    (repo / "user-change.txt").write_text("preserve me\n", encoding="utf-8")
    worktree_root = tmp_path / "worktrees"
    monkeypatch.setattr(auto_developer_module, "DEFAULT_WORKSPACE_ROOT", worktree_root)
    store = _queue(tmp_path, _safe_payload())

    def runner(args, **kwargs):
        if args[0] == "opencode":
            (Path(kwargs["cwd"]) / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
                "baseline = True\nagent_change = True\n", encoding="utf-8"
            )
            return subprocess.CompletedProcess(args, 0, "implemented\n", "")
        if args and args[0] == "git":
            if args[1] == "show-ref":
                return subprocess.CompletedProcess(args, 1, "", "")
            if args[1] == "worktree":
                workspace = Path(args[-2])
                workspace.mkdir(parents=True, exist_ok=True)
                shutil.copytree(repo / "creator_app", workspace / "creator_app")
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[1] == "status":
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[1] == "rev-parse":
                return subprocess.CompletedProcess(args, 0, "abc\n", "")
            if args[1] == "diff":
                return subprocess.CompletedProcess(args, 0, "", "")
        if args and (args[0].endswith("pytest") or args[0] == ".venv/bin/pytest"):
            return subprocess.CompletedProcess(args, 0, "1 passed\n", "")
        raise AssertionError("unexpected subprocess command")

    result = AutoDeveloper(
        store,
        repo=repo,
        evidence_dir=tmp_path / "evidence",
        runner=runner,
    ).run_once()

    assert result.state == "verified", result
    assert (repo / "user-change.txt").read_text(encoding="utf-8") == "preserve me\n"
    assert (repo / "creator_app" / "n8n_intelligence" / "analysis.py").read_text(
        encoding="utf-8"
    ) == "baseline = True\n"
    worktrees = list(worktree_root.iterdir())
    assert len(worktrees) == 1
    assert (worktrees[0] / "creator_app" / "n8n_intelligence" / "analysis.py").is_file()
