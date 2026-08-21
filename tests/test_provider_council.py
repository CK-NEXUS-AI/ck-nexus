from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.provider_council import (
    CouncilDecision,
    CouncilMode,
    CouncilPolicy,
    ProviderCouncil,
)
from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
    ProviderRouter,
)


@dataclass
class StubProvider:
    name: str
    output: str = "ok"
    available: bool = True
    fail: bool = False
    kind: ProviderKind = ProviderKind.CLOUD
    capabilities: ProviderCapabilities = ProviderCapabilities(
        features=frozenset({"text"}), models=("stub",)
    )

    def is_available(self) -> bool:
        return self.available

    async def invoke(self, prompt: str) -> str:
        if self.fail:
            raise RuntimeError("provider failure")
        return self.output


def council(tmp_path: Path, providers, **kwargs) -> ProviderCouncil:
    router = ProviderRouter(providers)
    return ProviderCouncil(
        router, AppendOnlyLedger(tmp_path / "council.jsonl"), **kwargs
    )


@pytest.mark.asyncio
async def test_consensus_requires_matching_quorum(tmp_path: Path):
    c = council(
        tmp_path,
        [
            StubProvider("a", "same"),
            StubProvider("b", "same"),
            StubProvider("c", "other"),
        ],
    )
    result = await c.execute("prompt", mode=CouncilMode.CONSENSUS)
    assert result.decision is CouncilDecision.COMPLETE
    assert result.successful == 3
    assert result.selected_output_digest is not None


@pytest.mark.asyncio
async def test_consensus_disagreement_needs_verification(tmp_path: Path):
    c = council(
        tmp_path,
        [
            StubProvider("a", "one"),
            StubProvider("b", "two"),
            StubProvider("c", "three"),
        ],
    )
    result = await c.execute("prompt", mode=CouncilMode.CONSENSUS)
    assert result.decision is CouncilDecision.NEEDS_VERIFICATION
    assert result.selected_output_digest is None


@pytest.mark.asyncio
async def test_adversarial_never_self_closes(tmp_path: Path):
    c = council(tmp_path, [StubProvider("a", "one"), StubProvider("b", "two")])
    result = await c.execute("prompt", mode=CouncilMode.ADVERSARIAL)
    assert result.decision is CouncilDecision.NEEDS_VERIFICATION
    assert result.successful == 2


@pytest.mark.asyncio
async def test_quorum_failure_is_fail_closed(tmp_path: Path):
    c = council(tmp_path, [StubProvider("a", fail=True), StubProvider("b", "ok")])
    result = await c.execute("prompt", mode=CouncilMode.PARALLEL)
    assert result.decision is CouncilDecision.QUORUM_FAILED
    assert result.successful == 1


@pytest.mark.asyncio
async def test_fast_invokes_only_one_provider(tmp_path: Path):
    c = council(tmp_path, [StubProvider("a", "one"), StubProvider("b", "two")])
    result = await c.execute("prompt", mode=CouncilMode.FAST)
    assert len(result.runs) == 1
    assert result.quorum == 1
    assert result.decision is CouncilDecision.COMPLETE


@pytest.mark.asyncio
async def test_cheap_prefers_local_without_claiming_price(tmp_path: Path):
    c = council(
        tmp_path,
        [
            StubProvider("cloud", "c"),
            StubProvider("local", "l", kind=ProviderKind.LOCAL),
        ],
    )
    result = await c.execute("prompt", mode=CouncilMode.CHEAP)
    assert result.runs[0].provider == "local"


@pytest.mark.asyncio
async def test_explicit_cost_rank_overrides_default(tmp_path: Path):
    c = council(
        tmp_path,
        [StubProvider("cloud-a", "a"), StubProvider("cloud-b", "b")],
        provider_cost_rank={"cloud-b": 1, "cloud-a": 9},
    )
    result = await c.execute("prompt", mode=CouncilMode.CHEAP)
    assert result.runs[0].provider == "cloud-b"


@pytest.mark.asyncio
async def test_capability_filter_and_max_parallel(tmp_path: Path):
    rich = ProviderCapabilities(features=frozenset({"text", "vision"}), models=("v",))
    c = council(
        tmp_path,
        [
            StubProvider("a", capabilities=rich),
            StubProvider("b"),
            StubProvider("c", capabilities=rich),
        ],
        policy=CouncilPolicy(max_parallel=2, minimum_quorum=2),
    )
    result = await c.execute(
        "prompt", mode=CouncilMode.DEEP, required_capabilities=("vision",)
    )
    assert [row.provider for row in result.runs] == ["a", "c"]
    assert result.decision is CouncilDecision.COMPLETE


@pytest.mark.asyncio
async def test_evidence_contains_digests_not_raw_outputs(tmp_path: Path):
    path = tmp_path / "council.jsonl"
    c = ProviderCouncil(
        ProviderRouter(
            [
                StubProvider("a", "TOP SECRET RESULT"),
                StubProvider("b", "TOP SECRET RESULT"),
            ]
        ),
        AppendOnlyLedger(path),
    )
    result = await c.execute("sensitive prompt", mode=CouncilMode.CONSENSUS)
    text = path.read_text(encoding="utf-8")
    assert result.evidence_ref
    assert "TOP SECRET RESULT" not in text
    assert "sensitive prompt" not in text
    assert '"raw_outputs_stored": false' in text


def test_policy_rejects_invalid_quorum():
    with pytest.raises(ValueError):
        CouncilPolicy(max_parallel=1, minimum_quorum=2)
