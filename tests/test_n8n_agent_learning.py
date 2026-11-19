import json
from pathlib import Path

from creator_app.n8n_intelligence.learning import AgentLearningMemory


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_learning_context_summarizes_outcomes_without_replaying_raw_output(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write(
        evidence / "one.json",
        {
            "state": "verified",
            "tests_ok": True,
            "changed_paths": ["creator_app/control_plane/example.py"],
            "assistant_output_tail": "RAW_OUTPUT_MARKER=do-not-copy-this",
        },
    )
    _write(
        evidence / "two.json",
        {"state": "failed", "reason": "assistant_timeout", "changed_paths": []},
    )
    _write(
        evidence / "three.json",
        {"state": "failed", "reason": "assistant_timeout", "changed_paths": []},
    )
    (evidence / "broken.json").write_text("not json", encoding="utf-8")

    context = AgentLearningMemory(evidence).context_for("fix the adapter")

    assert "verified outcomes: 1" in context
    assert "failed outcomes: 2" in context
    assert "assistant_timeout (2)" in context
    assert "creator_app/control_plane/example.py" in context
    assert "do-not-copy-this" not in context
    assert "RAW_OUTPUT_MARKER" not in context


def test_learning_context_is_bounded_and_empty_store_is_safe(tmp_path: Path):
    memory = AgentLearningMemory(tmp_path / "missing")
    assert "No prior verified outcomes" in memory.context_for("task")

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    for index in range(100):
        _write(
            evidence / f"{index:03}.json",
            {
                "state": "failed",
                "reason": "test_failure_" + ("x" * 100),
                "changed_paths": ["docs/design.md"],
            },
        )
    assert len(AgentLearningMemory(evidence, max_records=10).context_for("task")) <= 2500
