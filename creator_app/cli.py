from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MIN_FREE_BYTES = 512 * 1024 * 1024


def _state_dir() -> Path:
    return Path(os.getenv("CKNEXUS_STATE_DIR", Path.home() / ".ck-nexus")).expanduser()


def _pid_file() -> Path:
    return _state_dir() / "runtime.pid"


def _log_file() -> Path:
    return _state_dir() / "logs" / "runtime.log"


def _read_pid() -> int | None:
    try:
        value = int(_pid_file().read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None
    return value if value > 0 else None


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _progress(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}")


def install() -> int:
    print("CK-NEXUS — Installation check")
    _progress(1, 3, "Checking this computer...")
    state = _state_dir()
    state.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(state)
    if usage.free < MIN_FREE_BYTES:
        print("ERROR: Not enough free disk space. Keep at least 512 MB available.")
        return 2
    _progress(2, 3, "Preparing CK-NEXUS local files...")
    (state / "logs").mkdir(parents=True, exist_ok=True)
    required_modules = ("creator_app", "fastapi", "uvicorn")
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
    if missing:
        print("ERROR: Required CK-NEXUS packages are missing. Reinstall the package and try again.")
        return 2
    _progress(3, 3, "Verifying the runtime...")
    print("Installation ready. Start with: ck-nexus start")
    return 0


def start(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    pid = _read_pid()
    if pid and _process_alive(pid):
        print(f"CK-NEXUS is already running (PID {pid}).")
        return 0
    state = _state_dir()
    (state / "logs").mkdir(parents=True, exist_ok=True)
    log = _log_file().open("a", encoding="utf-8")
    command = [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", str(port)]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(0.2)
    if process.poll() is not None:
        print(f"ERROR: CK-NEXUS could not start. Check {_log_file()}.")
        return 1
    _pid_file().write_text(str(process.pid), encoding="utf-8")
    print(f"CK-NEXUS started: http://{host}:{port}")
    return 0


def stop() -> int:
    pid = _read_pid()
    if not pid or not _process_alive(pid):
        _pid_file().unlink(missing_ok=True)
        print("CK-NEXUS is not running.")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not _process_alive(pid):
            _pid_file().unlink(missing_ok=True)
            print("CK-NEXUS stopped.")
            return 0
        time.sleep(0.1)
    print(f"WARNING: Process {pid} is still stopping. Check status again shortly.")
    return 1


def status() -> int:
    pid = _read_pid()
    if pid and _process_alive(pid):
        print(f"CK-NEXUS status: running (PID {pid})")
        return 0
    _pid_file().unlink(missing_ok=True)
    print("CK-NEXUS status: stopped")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ck-nexus", description="CK-NEXUS simple runtime control")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install", help="check and prepare CK-NEXUS")
    start_parser = sub.add_parser("start", help="start CK-NEXUS in the background")
    start_parser.add_argument("--host", default=os.getenv("CKNEXUS_HOST", DEFAULT_HOST))
    start_parser.add_argument("--port", type=int, default=int(os.getenv("PORT", str(DEFAULT_PORT))))
    sub.add_parser("stop", help="stop CK-NEXUS")
    sub.add_parser("status", help="show current status")
    sub.add_parser("help", help="show commands")
    return parser


def main(argv: list[str] | None = None) -> int | None:
    args = build_parser().parse_args(argv)
    if args.command is None:
        from main import main as legacy_main

        legacy_main()
        return None
    if args.command == "install":
        return install()
    if args.command == "start":
        return start(host=args.host, port=args.port)
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()
    build_parser().print_help()
    return 0
