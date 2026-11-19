from pathlib import Path

from ops.vps.scripts.cknexus_n8n_auto_developer import build_parser, run


def test_cli_defaults_are_bounded():
    args = build_parser().parse_args([])
    assert args.timeout == 180
    assert args.repo == Path("/root/ck-nexus")


def test_cli_idle_without_tasks(tmp_path: Path, capsys):
    code = run(tmp_path / "repo", tmp_path / "tasks.db", tmp_path / "evidence", 30)
    output = capsys.readouterr().out
    assert code == 0
    assert '"state": "idle"' in output
