from __future__ import annotations

import main
from creator_app import unified


def test_compatibility_entrypoint_uses_canonical_app() -> None:
    assert main.app is unified.app


def test_compatibility_entrypoint_uses_canonical_server() -> None:
    assert main.main is unified.main
