from __future__ import annotations

from datetime import UTC, datetime

from idea_engine.knowledge_repository import _postgres_timestamp


def test_postgres_timestamp_normalizes_zulu_time_to_utc_datetime() -> None:
    result = _postgres_timestamp("2026-09-03T00:00:00Z")

    assert result == datetime(2026, 9, 3, tzinfo=UTC)
    assert result.tzinfo is UTC


def test_postgres_timestamp_treats_naive_iso_time_as_utc() -> None:
    result = _postgres_timestamp("2026-09-03T12:34:56")

    assert result == datetime(2026, 9, 3, 12, 34, 56, tzinfo=UTC)


def test_postgres_timestamp_preserves_nullable_freshness_boundary() -> None:
    assert _postgres_timestamp(None) is None
