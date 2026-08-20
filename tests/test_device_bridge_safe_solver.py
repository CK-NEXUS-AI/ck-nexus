from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.device_bridge.safe_solver import SafeProblemSolver, SolverPolicyError


def test_read_text_redacts_secrets_and_returns_digest(tmp_path: Path) -> None:
    target = tmp_path / "sample.env"
    target.write_text(
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\n"
        "Authorization: Bearer top-secret-token\n",
        encoding="utf-8",
    )
    solver = SafeProblemSolver(tmp_path)

    result = solver.read_text("sample.env")

    assert result["redacted"] is True
    assert "abcdefghijklmnopqrstuvwxyz" not in result["content"]
    assert "top-secret-token" not in result["content"]
    assert result["sha256"]


def test_path_traversal_is_denied(tmp_path: Path) -> None:
    solver = SafeProblemSolver(tmp_path)

    with pytest.raises(SolverPolicyError, match="path_outside_workspace"):
        solver.read_text("../outside.txt")


def test_absolute_path_is_denied(tmp_path: Path) -> None:
    solver = SafeProblemSolver(tmp_path)

    with pytest.raises(SolverPolicyError, match="path_outside_workspace"):
        solver.read_text("/etc/passwd")


def test_symlink_is_denied_even_when_target_is_inside_workspace(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("safe", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    solver = SafeProblemSolver(tmp_path)

    with pytest.raises(SolverPolicyError, match="symlink_denied"):
        solver.read_text("link.txt")


def test_json_analysis_does_not_echo_raw_values(tmp_path: Path) -> None:
    solver = SafeProblemSolver(tmp_path)
    secret_value = "this-value-must-not-be-returned"

    result = solver.analyze_json(f'{{"name":"demo","secret":"{secret_value}"}}')

    assert result["valid"] is True
    assert result["type"] == "dict"
    assert result["count"] == 2
    assert secret_value not in repr(result)


def test_code_review_is_non_executing_and_flags_shell_true(tmp_path: Path) -> None:
    solver = SafeProblemSolver(tmp_path)
    code = 'subprocess.run("echo test", shell=True)\nos.system("id")\n'

    result = solver.review_code(code)

    assert result["executed"] is False
    assert result["finding_count"] == 2


def test_file_hash_is_bounded_and_content_free(tmp_path: Path) -> None:
    target = tmp_path / "artifact.txt"
    target.write_text("evidence", encoding="utf-8")
    solver = SafeProblemSolver(tmp_path)

    result = solver.sha256_file("artifact.txt")

    assert result["size"] == 8
    assert len(result["sha256"]) == 64
    assert "content" not in result
