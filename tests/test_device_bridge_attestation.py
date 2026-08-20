from __future__ import annotations

from pathlib import Path

import pytest

import creator_app.device_bridge.attestation as attestation
from creator_app.device_bridge.attestation import AttestationError, CheckoutAttestation
from creator_app.device_bridge.descriptor_generator import descriptor_sha256
from creator_app.device_bridge.mcp_server_v2 import TOOL_SPECS


def test_measure_checkout_requires_clean_exact_git_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["true", "a" * 40, "b" * 40, ""])
    monkeypatch.setattr(attestation, "_run_git", lambda _root, *_args: next(responses))

    result = attestation.measure_checkout(tmp_path)

    assert result == CheckoutAttestation(commit_sha="a" * 40, tree_sha="b" * 40, clean=True)


def test_measure_checkout_denies_dirty_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["true", "a" * 40, "b" * 40, " M creator_app/example.py"])
    monkeypatch.setattr(attestation, "_run_git", lambda _root, *_args: next(responses))

    with pytest.raises(AttestationError, match="dirty_checkout_denied"):
        attestation.measure_checkout(tmp_path)


@pytest.mark.asyncio
async def test_attested_descriptor_binds_source_tree_and_live_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / "creator_app" / "device_bridge" / "mcp_server_v2.py"
    script.parent.mkdir(parents=True)
    script.write_text("# fixture\n", encoding="utf-8")

    monkeypatch.setattr(
        attestation,
        "measure_checkout",
        lambda _root: CheckoutAttestation(commit_sha="a" * 40, tree_sha="b" * 40, clean=True),
    )

    async def fake_probe(_root: str | Path) -> list[dict[str, str]]:
        return [
            {"name": name, "description": description}
            for name, description in TOOL_SPECS
        ]

    monkeypatch.setattr(attestation, "probe_runtime_registry", fake_probe)

    descriptor = await attestation.build_attested_descriptor(tmp_path)

    assert descriptor["integrity"]["source_commit"] == "a" * 40
    assert descriptor["integrity"]["source_tree"] == "b" * 40
    assert descriptor["integrity"]["checkout_clean"] is True
    assert len(descriptor["integrity"]["runtime_registry_sha256"]) == 64
    assert len(descriptor_sha256(descriptor)) == 64


@pytest.mark.asyncio
async def test_attested_descriptor_denies_registry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        attestation,
        "measure_checkout",
        lambda _root: CheckoutAttestation(commit_sha="a" * 40, tree_sha="b" * 40, clean=True),
    )

    async def fake_probe(_root: str | Path) -> list[dict[str, str]]:
        return [{"name": "unexpected_tool", "description": "drift"}]

    monkeypatch.setattr(attestation, "probe_runtime_registry", fake_probe)

    with pytest.raises(AttestationError, match="runtime_registry_drift"):
        await attestation.build_attested_descriptor(tmp_path)
