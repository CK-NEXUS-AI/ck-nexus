$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
}

if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.example" ".env.local"
}

& ".\.venv\Scripts\python.exe" "main.py"

