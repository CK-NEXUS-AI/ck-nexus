from pathlib import Path

from ops.vps.scripts import cknexus_n8n_auto_developer as auto_developer_cli
from ops.vps.scripts.cknexus_n8n_auto_developer import build_parser, run


def test_cli_defaults_are_bounded():
    args = build_parser().parse_args([])
    assert args.timeout == 180
    assert args.repo == Path("/root/ck-nexus")


def test_cli_idle_without_tasks(tmp_path: Path, capsys, monkeypatch):
    database = tmp_path / "tasks.db"
    monkeypatch.setattr(auto_developer_cli, "_task_database_path", lambda _path: database)
    repo = tmp_path / "repo"
    repo.mkdir()
    code = run(repo, database, tmp_path / "evidence", 30)
    output = capsys.readouterr().out
    assert code == 0
    assert '"state": "idle"' in output
