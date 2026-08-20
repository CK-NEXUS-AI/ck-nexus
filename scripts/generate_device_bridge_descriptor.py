"""Emit a measured CK-NEXUS device-bridge descriptor from a clean local checkout."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from creator_app.device_bridge.attestation import AttestationError, build_attested_descriptor


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate canonical clean-room MCP descriptor after local attestation."
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="CK-NEXUS checkout root. Defaults to current directory.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        descriptor = asyncio.run(build_attested_descriptor(Path(args.workspace)))
    except (AttestationError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:160]}, sort_keys=True))
        return 1

    payload = json.dumps(
        descriptor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(payload)
    print(f"descriptor_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
