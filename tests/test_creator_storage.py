from __future__ import annotations

from datetime import UTC, datetime

from creator_app.schemas import RunResult
from creator_app.storage import RunStore


def sample_run(run_id: str, created_at: datetime) -> RunResult:
    return RunResult(
        id=run_id,
        session_id="session-one",
        agent_id="content-strategist",
        agent_name="Content Strategist",
        prompt="สร้างไอเดียคอนเทนต์",
        audience="ผู้เริ่มต้น",
        platform="Facebook",
        tone="ให้ความรู้",
        language="ไทย",
        content="# Result",
        model="gpt-5-mini",
        mode="mock",
        status="completed",
        duration_ms=1,
        created_at=created_at,
    )


def test_store_round_trip_and_order(tmp_path):
    store = RunStore(tmp_path / "store.db")
    store.initialize()
    older = datetime(2026, 8, 5, 1, tzinfo=UTC)
    newer = datetime(2026, 8, 5, 2, tzinfo=UTC)
    store.save(sample_run("run_old", older))
    store.save(sample_run("run_new", newer))

    assert [run.id for run in store.list(limit=10)] == ["run_new", "run_old"]
    assert store.get("run_new").language == "ไทย"
    assert store.delete_session("session-one") == 2
    assert store.list(limit=10) == []
