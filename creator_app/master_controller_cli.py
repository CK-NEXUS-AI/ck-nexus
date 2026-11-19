"""CLI for CK-NEXUS Master Controller V1."""

from __future__ import annotations

import argparse
import json

from creator_app.master_controller import MasterController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ck-nexus-control")
    parser.add_argument(
        "command",
        nargs="*",
        help="Command to classify and route. Empty input defaults to CK-NEXUS RUN.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    command = " ".join(args.command).strip() or "CK-NEXUS RUN"
    plan = MasterController().plan(command)
    print(json.dumps(plan.as_dict(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
