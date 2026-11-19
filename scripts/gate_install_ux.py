from __future__ import annotations

import contextlib
import importlib
import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

cli = importlib.import_module("creator_app.cli")


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        state = Path(raw)
        usage = type("Usage", (), {"free": cli.MIN_FREE_BYTES})()
        with (
            patch.dict("os.environ", {"CKNEXUS_STATE_DIR": str(state)}, clear=False),
            patch.object(cli.shutil, "disk_usage", return_value=usage),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            check("install_preflight", cli.install() == 0)
        check("install_state", (state / "logs").is_dir())

        class FakeProcess:
            pid = 2468

            def poll(self):
                return None

        commands: list[list[str]] = []

        def fake_popen(command, **_kwargs):
            commands.append(command)
            return FakeProcess()

        with (
            patch.dict("os.environ", {"CKNEXUS_STATE_DIR": str(state)}, clear=False),
            patch.object(cli.subprocess, "Popen", side_effect=fake_popen),
            patch.object(cli.time, "sleep", return_value=None),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            check("start_command", cli.start(port=8123) == 0)
        check("start_pid", (state / "runtime.pid").read_text(encoding="utf-8") == "2468")
        check("start_port", commands[0][-1] == "8123")

        with (
            patch.dict("os.environ", {"CKNEXUS_STATE_DIR": str(state)}, clear=False),
            patch.object(cli, "_process_alive", return_value=False),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            check("stale_status", cli.status() == 1)
        check("stale_pid_removed", not (state / "runtime.pid").exists())

    parser = cli.build_parser()
    check("commands_present", set(parser._subparsers._group_actions[0].choices) == {
        "install", "start", "stop", "status", "help"
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
