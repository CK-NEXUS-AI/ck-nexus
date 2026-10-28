import hashlib
import json
import subprocess
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
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


def test_successful_run_requires_tests_and_keeps_head_unchanged(tmp_path: Path):
    store = _queue(tmp_path, _safe_payload())
    repo = tmp_path / "repo"
    repo.mkdir()
    state = {"head": "abc", "status": "", "codex_done": False}
    codex_commands = []
    pytest_invocations = []

    def runner(args, **kwargs):
        if args[:3] == ["git", "show-ref", "--verify"]:
            return subprocess.CompletedProcess(args, 1, "", "")
        if args[:3] == ["git", "worktree", "add"]:
            Path(args[-2]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "status", "--porcelain=v1"]:
            status = " M creator_app/n8n_intelligence/analysis.py\n" if state["codex_done"] else ""
            return subprocess.CompletedProcess(args, 0, status, "")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, state["head"] + "\n", "")
        if args[:3] == ["git", "diff", "--check"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0].endswith("pytest") and args[1:] == [
            "-q",
            "tests/test_n8n_intelligence_analysis.py",
        ]:
            pytest_invocations.append((Path(kwargs["cwd"]), kwargs.get("env", {})))
            return subprocess.CompletedProcess(args, 0, "1 passed\n", "")
        if args[:2] == ["codex", "exec"]:
            codex_commands.append(args)
            state["codex_done"] = True
            return subprocess.CompletedProcess(args, 0, "implemented\n", "")
        raise AssertionError(args)

    result = AutoDeveloper(
        store, repo=repo, evidence_dir=tmp_path / "evidence", runner=runner
    ).run_once()
    assert result.state == "verified"
    assert result.tests_ok is True
    test_cwd, test_env = pytest_invocations[0]
    assert test_env["PYTHONPATH"].split(":")[0] == str(test_cwd)
    assert "--approve-for-me" in codex_commands[0]
    assert "--sandbox" not in codex_commands[0]
    assert "--dangerously-bypass-approvals-and-sandbox" not in codex_commands[0]
    assert store.get("n8n-job-1")["state"] == "completed"
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert evidence["head_unchanged"] is True
    assert evidence["index_clean"] is True
    assert evidence["team_workflow_required"] is True
    assert evidence["team_execution_mode"] == "single-agent-multi-perspective"
    assert evidence["independent_council_vote"] is False
    assert evidence["team_workflow_roles"] == [
        "Researcher",
        "Architect",
        "Implementer",
        "Independent Reviewer",
        "Test and Evidence Owner",
        "Synthesis Lead",
    ]


def test_dirty_primary_repo_uses_isolated_git_worktree(tmp_path: Path):

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
    store = _queue(tmp_path, _safe_payload())

    def runner(args, **kwargs):
        if args[0] == "codex":
            (Path(kwargs["cwd"]) / "creator_app" / "n8n_intelligence" / "analysis.py").write_text(
                "baseline = True\nagent_change = True\n", encoding="utf-8"
            )
            return subprocess.CompletedProcess(args, 0, "implemented\n", "")
        if args and (args[0].endswith("pytest") or args[0] == ".venv/bin/pytest"):
            return subprocess.CompletedProcess(args, 0, "1 passed\n", "")
        return subprocess.run(args, **kwargs)

    result = AutoDeveloper(
        store,
        repo=repo,
        evidence_dir=tmp_path / "evidence",
        runner=runner,
    ).run_once()

    assert result.state == "verified"
    assert (repo / "user-change.txt").read_text(encoding="utf-8") == "preserve me\n"
    assert (repo / "creator_app" / "n8n_intelligence" / "analysis.py").read_text(
        encoding="utf-8"
    ) == "baseline = True\n"
    worktrees = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert str(worktree_root) in worktrees


def test_auto_developer_prompt_requires_team_assignments_and_evidence(tmp_path: Path):
    store = _queue(tmp_path, _safe_payload())
    repo = tmp_path / "repo"
    repo.mkdir()
    developer = AutoDeveloper(store, repo=repo, evidence_dir=tmp_path / "evidence")

    prompt = developer._prompt(_safe_payload())

    assert "MANDATORY TEAM WORKFLOW" in prompt
    assert "Researcher" in prompt
    assert "Architect" in prompt
    assert "Implementer" in prompt
    assert "Independent Reviewer" in prompt
    assert "Test and Evidence Owner" in prompt
    assert "Do not claim independent votes" in prompt
    assert "No Evidence -> No Done" in prompt
    assert "Each role returns" in prompt
    assert "high-risk" in prompt.lower()
    assert "ALLOWED EDIT PATHS" in prompt
    assert "creator_app/n8n_intelligence/analysis.py" in prompt
    assert "creator_app/control_plane/fast_probe.py" in prompt
    assert "Do not edit any path outside this list" in prompt


def test_failed_assistant_exit_records_redacted_diagnostic_from_stdout(tmp_path: Path):
    store = _queue(tmp_path, _safe_payload())
    repo = tmp_path / "repo"
    repo.mkdir()

    def runner(args, **kwargs):
        if args[:3] == ["git", "show-ref", "--verify"]:
            return subprocess.CompletedProcess(args, 1, "", "")
        if args[:3] == ["git", "worktree", "add"]:
            Path(args[-2]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "status", "--porcelain=v1"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "abc123\n", "")
        if args[:2] == ["codex", "exec"]:
            return subprocess.CompletedProcess(
                args,
                2,
                "Error: API_KEY=supersecretvalue123456 "
                "Authorization: Bearer bearersecretvalue123456\n",
                "",
            )
        raise AssertionError(args)

    result = AutoDeveloper(
        store, repo=repo, evidence_dir=tmp_path / "evidence", runner=runner
    ).run_once()
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))

    assert result.state == "verification_failed"
    assert evidence["exit_code"] == 2
    assert evidence["assistant_error"]
    assert "Error" in evidence["assistant_error"]
    serialized = json.dumps(evidence)
    assert "supersecretvalue123456" not in serialized
    assert "bearersecretvalue123456" not in serialized
    assert "[redacted]" in evidence["assistant_error"]


def test_existing_clean_workspace_is_reused_but_dirty_workspace_is_preserved_in_fallback(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)

    job_id = "n8n-job-1"
    key = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:16]
    branch = f"cknexus/auto-dev/{key}"
    workspace_root = tmp_path / "worktrees"
    workspace = workspace_root / key
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(workspace), "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    developer = AutoDeveloper(
        _queue(tmp_path, _safe_payload()),
        repo=repo,
        evidence_dir=tmp_path / "evidence",
        workspace_root=workspace_root,
    )

    reused, reused_branch = developer._create_workspace(job_id)
    assert reused == workspace
    assert reused_branch == branch

    sentinel = workspace / "unverified-change.txt"
    sentinel.write_text("preserve this failed attempt\n", encoding="utf-8")
    main_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    base_key = f"{key}-{main_head[:12]}"
    fallback_workspace = workspace_root / base_key
    fallback_branch = f"cknexus/auto-dev/{base_key}"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            fallback_branch,
            str(fallback_workspace),
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fallback_sentinel = fallback_workspace / "fallback-change.txt"
    fallback_sentinel.write_text("preserve second failed attempt\n", encoding="utf-8")
    fresh_workspace, fresh_branch = developer._create_workspace(job_id)
    fresh_head = subprocess.run(
        ["git", "-C", str(fresh_workspace), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert fresh_workspace != workspace
    assert fresh_workspace != fallback_workspace
    assert fresh_branch != branch
    assert fresh_head == main_head
    assert sentinel.read_text(encoding="utf-8") == "preserve this failed attempt\n"
    assert fallback_sentinel.read_text(encoding="utf-8") == "preserve second failed attempt\n"


def test_stale_clean_workspace_is_preserved_and_new_workspace_uses_current_head(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)

    job_id = "stale-workspace-job"
    key = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:16]
    old_workspace = tmp_path / "worktrees" / key
    old_branch = f"cknexus/auto-dev/{key}"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-b", old_branch, str(old_workspace), "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )

    (repo / "new-main-file.txt").write_text("new main revision\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "new-main-file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "advance main"], check=True)
    main_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()

    developer = AutoDeveloper(
        _queue(tmp_path, _safe_payload()),
        repo=repo,
        evidence_dir=tmp_path / "evidence",
        workspace_root=tmp_path / "worktrees",
    )
    fresh_workspace, fresh_branch = developer._create_workspace(job_id)
    fresh_head = subprocess.run(
        ["git", "-C", str(fresh_workspace), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert fresh_workspace != old_workspace
    assert fresh_head == main_head
    assert fresh_branch != old_branch
    assert (old_workspace / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
    assert not (old_workspace / "new-main-file.txt").exists()


def test_failed_tests_record_redacted_diagnostic(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    developer = AutoDeveloper(
        _queue(tmp_path, _safe_payload()),
        repo=repo,
        evidence_dir=tmp_path / "evidence",
    )

    def runner(args, **kwargs):
        if args[0].endswith("pytest"):
            return subprocess.CompletedProcess(
                args,
                1,
                (
                    "....\nE AssertionError: API_KEY=supersecretvalue123456\n"
                    "FAILED tests/test_example.py\n"
                ),
                "",
            )
        if args[:3] == ["git", "diff", "--check"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(args)

    developer.runner = runner
    result = developer._run_tests(
        tmp_path, ["creator_app/n8n_intelligence/analysis.py"]
    )

    assert result["ok"] is False
    assert result["pytest_exit_code"] == 1
    assert "AssertionError" in result["pytest_output"]
    assert "supersecretvalue123456" not in result["pytest_output"]
    assert "[redacted]" in result["pytest_output"]
    assert result["diff_exit_code"] == 0


def test_no_python_changes_are_not_applicable_but_diff_check_must_pass(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    developer = AutoDeveloper(
        _queue(tmp_path, _safe_payload()),
        repo=repo,
        evidence_dir=tmp_path / "evidence",
    )

    def runner(args, **kwargs):
        assert args[:3] == ["git", "diff", "--check"]
        return subprocess.CompletedProcess(args, 0, "", "")

    developer.runner = runner
    result = developer._run_tests(tmp_path, ["docs/operations.md"])

    assert result["test_targets"] == []
    assert result["pytest_exit_code"] is None
    assert result["pytest_output"] == "no_python_changes_tests_not_applicable"
    assert result["diff_exit_code"] == 0
    assert result["ok"] is True
