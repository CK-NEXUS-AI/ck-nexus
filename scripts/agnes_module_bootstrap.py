#!/usr/bin/env python3
"""Render the AGNES optional dependency plan without mutating the host."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from creator_app.agnes.fabric import AGNESCapabilityFabric


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit dependency plan as JSON")
    return parser


def main() -> int:
    args = _parser().parse_args()
    plan = AGNESCapabilityFabric().external_dependency_plan()
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print("AGNES optional Python distributions:")
        for item in plan["python_packages"]:
            print(f"  - {item}")
        print("AGNES optional host binaries (operator-managed):")
        for item in plan["host_binaries"]:
            print(f"  - {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
