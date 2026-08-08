from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def main() -> int:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required. Install Node.js 18 or later first.")

    project_root = Path(__file__).resolve().parents[1]
    prefix = project_root / ".tools" / "codex"
    cache = project_root / ".cache" / "npm"
    command = [
        npm,
        "install",
        "--cache",
        str(cache),
        "--prefix",
        str(prefix),
        "@openai/codex@latest",
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        return completed.returncode

    executable = prefix / "node_modules" / ".bin" / "codex"
    print(f"Codex CLI installed at {executable}")
    print("Run it with `codex login`, then set CKNEXUS_CODEX_BIN to this path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
