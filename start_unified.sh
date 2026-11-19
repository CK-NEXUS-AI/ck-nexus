#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ ! -d .venv ]; then
  python -m venv .venv
  .venv/bin/python -m pip install -e ".[dev]"
fi

if [ ! -f .env.local ]; then
  cp .env.example .env.local
fi

exec .venv/bin/python -m creator_app.unified
