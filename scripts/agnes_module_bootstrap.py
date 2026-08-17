#!/usr/bin/env python3
"""Inventory AGNES optional runtime dependencies without mutating the host by default."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from creator_app.agnes.fabric import AGNESCapabilityFabric


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit dependency plan as JSON")
    parser.add_argument(
        "--apply-python",
        action="store_true",
        help="install optional Python distributions into the current interpreter environment",
    )
    parser.add_argument(
        "--i-understand-this-mutates-the-host",
        action="store_true",
        help="required together with --apply-python",
    )
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

    if not args.apply_python:
        return 0
    if not args.i_understand_this_mutates_the_host:
        print("refusing mutation: acknowledgement flag is required", file=sys.stderr)
        return 2

    command = [sys.executable, "-m", "pip", "install", *plan["python_packages"]]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
