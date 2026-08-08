from __future__ import annotations

from pathlib import Path

from creator_app.config import Settings, _as_bool, _as_int


def test_boolean_parser():
    assert _as_bool("true") is True
    assert _as_bool("ON") is True
    assert _as_bool("0") is False
    assert _as_bool(None, default=True) is True


def test_integer_parser_uses_bounds_and_safe_default():
    assert _as_int("12", default=5, minimum=1, maximum=20) == 12
    assert _as_int("999", default=5, minimum=1, maximum=20) == 20
    assert _as_int("invalid", default=5, minimum=1, maximum=20) == 5


def test_runtime_home_controls_relative_database_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_DATABASE_PATH", "state/creator.db")
    configured = Settings.from_env()
    assert configured.database_path == tmp_path / "state" / "creator.db"
