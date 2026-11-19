from pathlib import Path

from ops.vps.scripts.cknexus_n8n_intelligence import build_parser, run


def test_cli_parser_has_bounded_defaults():
    args = build_parser().parse_args([])
    assert args.max_executions == 50
    assert args.slow_seconds == 30.0


def test_cli_run_returns_failure_without_leaking_secret(tmp_path: Path, capsys):
    class BrokenClient:
        def list_executions(self):
            raise RuntimeError("Authorization: Bearer TOP-SECRET")

    code = run(BrokenClient(), tmp_path / "events.db", tmp_path / "tasks.db", 30.0, 50)
    output = capsys.readouterr().out
    assert code == 1
    assert "TOP-SECRET" not in output
