from pathlib import Path

from creator_app import sqlite_security
from ops.vps.scripts.cknexus_n8n_auto_developer import build_parser, run


def test_cli_defaults_are_bounded():
    args = build_parser().parse_args([])
    assert args.timeout == 180
    assert args.repo == Path("/root/ck-nexus")


def test_cli_idle_without_tasks(tmp_path: Path, capsys, monkeypatch):
    database = tmp_path / "tasks.db"
    approved = dict(sqlite_security._APPROVED_SQLITE_DATABASES)
    approved[str(database)] = database
    monkeypatch.setattr(sqlite_security, "_APPROVED_SQLITE_DATABASES", approved)
    code = run(tmp_path / "repo", database, tmp_path / "evidence", 30)
    output = capsys.readouterr().out
    assert code == 0
    assert '"state": "idle"' in output
