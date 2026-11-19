from __future__ import annotations

from pathlib import Path

import pytest

from scripts import package_buyer_delivery as delivery


def test_version_rejects_path_traversal_before_writing() -> None:
    with pytest.raises(ValueError, match="safe filename token"):
        delivery.build_package("../../outside")


def test_tracked_files_rejects_parent_traversal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        delivery.subprocess,
        "check_output",
        lambda *_args, **_kwargs: b"../outside.txt\x00",
    )
    with pytest.raises(RuntimeError, match="unsafe tracked path"):
        delivery.tracked_files()


def test_validated_child_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "package"
    root.mkdir()
    with pytest.raises(RuntimeError, match="escapes package root"):
        delivery.validated_child(root, root / ".." / "outside.txt")
