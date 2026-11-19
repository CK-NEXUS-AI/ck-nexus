from pathlib import Path

from creator_app.n8n_intelligence.models import N8NExecutionEvent
from creator_app.n8n_intelligence.store import N8NIntelligenceStore


def make_event(event_id="e1"):
    return N8NExecutionEvent(
        event_id,
        "exec-1",
        "w1",
        "WF",
        "error",
        "high",
        "failure",
        "boom",
        "2026-10-24T00:00:00Z",
        {},
    )


def test_store_deduplicates_and_counts_repeats(tmp_path: Path):
    store = N8NIntelligenceStore(tmp_path / "events.db")
    first = store.record_event(make_event())
    second = store.record_event(make_event())
    assert first == (True, 1)
    assert second == (False, 2)
    assert (tmp_path / "events.db").stat().st_mode & 0o777 == 0o600


def test_checkpoint_round_trip(tmp_path: Path):
    store = N8NIntelligenceStore(tmp_path / "events.db")
    assert store.checkpoint() is None
    store.set_checkpoint("cursor-1")
    assert store.checkpoint() == "cursor-1"
