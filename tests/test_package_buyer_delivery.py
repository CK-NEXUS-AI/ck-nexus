from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path("scripts/package_buyer_delivery.py")
SPEC = importlib.util.spec_from_file_location("package_buyer_delivery", MODULE_PATH)
assert SPEC and SPEC.loader
buyer_delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(buyer_delivery)


def test_output_directory_accepts_path_inside_repository(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    monkeypatch.setattr(buyer_delivery, "ROOT", repository)
    destination = repository / "dist" / "buyer-delivery"

    assert buyer_delivery.validate_output_directory(destination) == destination


def test_output_directory_rejects_path_outside_repository(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside"
    monkeypatch.setattr(buyer_delivery, "ROOT", repository)

    with pytest.raises(ValueError, match="outside the repository root"):
        buyer_delivery.validate_output_directory(outside)


def test_output_directory_rejects_symlink_escape(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repository / "export"
    link.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(buyer_delivery, "ROOT", repository)

    with pytest.raises(ValueError, match="outside the repository root"):
        buyer_delivery.validate_output_directory(link)
