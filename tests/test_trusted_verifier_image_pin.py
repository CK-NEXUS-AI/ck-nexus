from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verifier_image_requires_explicit_immutable_base_pin() -> None:
    pinned = (ROOT / ".github/verifier-image/base-image.txt").read_text().strip()
    dockerfile = (ROOT / ".github/verifier-image/Dockerfile").read_text()
    workflow = (ROOT / ".github/workflows/trusted-verifier-image-ci.yml").read_text()

    assert re.fullmatch(r"python@sha256:[0-9a-f]{64}", pinned)
    assert dockerfile.splitlines()[0] == "ARG BASE_IMAGE"
    assert "ARG BASE_IMAGE=" not in dockerfile
    assert '--build-arg "BASE_IMAGE=$BASE_IMAGE"' in workflow
