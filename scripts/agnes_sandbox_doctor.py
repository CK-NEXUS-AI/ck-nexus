from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creator_app.agnes.execution.sandbox import LinuxNamespaceRunner, SandboxPolicy  # noqa: E402


async def main_async(repository_root: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="agnes-sandbox-doctor-") as raw:
        root = Path(raw)
        work = root / "work"
        work.mkdir()
        probe = work / "probe.py"
        probe.write_text(
            "import pathlib,socket\n"
            "host_visible=pathlib.Path('/etc/passwd').exists()\n"
            "s=socket.socket(); s.settimeout(0.2)\n"
            "network='open'\n"
            "try: s.connect(('1.1.1.1',80))\n"
            "except Exception: network='blocked'\n"
            "print(f'host_visible={host_visible} network={network}')\n",
            encoding="utf-8",
        )
        policy = SandboxPolicy(base_dir=root / "sandbox", repository_root=repository_root)
        try:
            runner = LinuxNamespaceRunner(policy)
            health = await runner.health()
            if not health.get("ready"):
                print(json.dumps({"status": "BLOCKED", "health": health}, sort_keys=True))
                return 2
            result = await runner.run(
                workspace=work,
                execution_id="doctor",
                command=["python", "/workspace/probe.py"],
                timeout_seconds=10,
            )
            passed = (
                result.returncode == 0
                and "host_visible=False" in result.stdout
                and "network=blocked" in result.stdout
            )
            payload = {
                "status": "PASS" if passed else "FAIL",
                "backend": runner.backend_name,
                "production_safe": runner.production_safe,
                "health": health,
                "probe": {
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                },
            }
            print(json.dumps(payload, sort_keys=True))
            return 0 if passed else 1
        except Exception as exc:
            print(json.dumps({"status": "BLOCKED", "reason": type(exc).__name__}, sort_keys=True))
            return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    return asyncio.run(main_async(Path(args.repository_root).resolve()))


if __name__ == "__main__":
    raise SystemExit(main())
